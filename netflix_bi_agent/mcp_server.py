from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from mcp.server.fastmcp import FastMCP
from psycopg2.extras import RealDictCursor

from .db import connect
from .sql_safety import validate_readonly_sql


SERVER_INSTRUCTIONS = (
    "Netflix BI Supabase server. Inspect schema before writing SQL. "
    "Use PostgreSQL SELECT/WITH only; never mutate data. Multi-value fields "
    "such as genres, countries, directors, and cast use bridge tables. "
    "Return SQL plus a concise business explanation."
)

mcp = FastMCP("Netflix BI Supabase", instructions=SERVER_INSTRUCTIONS)


def _json_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _json_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{key: _json_value(value) for key, value in row.items()} for row in rows]


def _query_all(query: str, params: tuple[Any, ...] = tuple()) -> list[dict[str, Any]]:
    with connect(env_var="BI_AGENT_DB_URL") as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("set statement_timeout = %s", (15000,))
            if params:
                cur.execute(query, params)
            else:
                cur.execute(query)
            rows = cur.fetchall()
    return _json_rows([dict(row) for row in rows])


def _ensure_safe_identifier(identifier: str) -> str:
    if (
        not isinstance(identifier, str)
        or not identifier
        or not identifier.replace("_", "").isalnum()
        or not identifier[0].isalpha()
    ):
        raise ValueError("Table name must be a simple public schema identifier.")
    return identifier


@mcp.tool()
def get_schema_summary() -> dict[str, Any]:
    """Return the public Netflix BI schema tables and columns."""
    tables = _query_all(
        """
        select table_name, table_type
        from information_schema.tables
        where table_schema = 'public'
          and (
              table_name like 'dim_%'
              or table_name like 'fact_%'
              or table_name like 'bridge_%'
          )
        order by table_name
        """
    )
    columns = _query_all(
        """
        select table_name, column_name, data_type, is_nullable
        from information_schema.columns
        where table_schema = 'public'
          and (
              table_name like 'dim_%'
              or table_name like 'fact_%'
              or table_name like 'bridge_%'
          )
        order by table_name, ordinal_position
        """
    )
    return {"tables": tables, "columns": columns}


@mcp.tool()
def describe_table(table_name: str) -> dict[str, Any]:
    """Describe columns, primary keys, and foreign keys for one public table."""
    safe_table = _ensure_safe_identifier(table_name)
    relation = _query_all(
        """
        select table_name, table_type
        from information_schema.tables
        where table_schema = 'public'
          and table_name = %s
        """,
        (safe_table,),
    )
    if not relation:
        return {"table_name": safe_table, "exists": False, "columns": [], "primary_keys": [], "foreign_keys": []}

    columns = _query_all(
        """
        select column_name, data_type, is_nullable, column_default
        from information_schema.columns
        where table_schema = 'public'
          and table_name = %s
        order by ordinal_position
        """,
        (safe_table,),
    )
    primary_keys = _query_all(
        """
        select kcu.column_name
        from information_schema.table_constraints tc
        join information_schema.key_column_usage kcu
          on tc.constraint_name = kcu.constraint_name
         and tc.table_schema = kcu.table_schema
        where tc.table_schema = 'public'
          and tc.table_name = %s
          and tc.constraint_type = 'PRIMARY KEY'
        order by kcu.ordinal_position
        """,
        (safe_table,),
    )
    foreign_keys = _query_all(
        """
        select
            kcu.column_name,
            ccu.table_name as foreign_table_name,
            ccu.column_name as foreign_column_name
        from information_schema.table_constraints tc
        join information_schema.key_column_usage kcu
          on tc.constraint_name = kcu.constraint_name
         and tc.table_schema = kcu.table_schema
        join information_schema.constraint_column_usage ccu
          on ccu.constraint_name = tc.constraint_name
         and ccu.table_schema = tc.table_schema
        where tc.constraint_type = 'FOREIGN KEY'
          and tc.table_schema = 'public'
          and tc.table_name = %s
        order by kcu.column_name
        """,
        (safe_table,),
    )
    return {
        "table_name": safe_table,
        "exists": True,
        "columns": columns,
        "primary_keys": primary_keys,
        "foreign_keys": foreign_keys,
    }


@mcp.tool()
def get_relationships() -> dict[str, Any]:
    """Return foreign-key relationships in the public Netflix BI schema."""
    relationships = _query_all(
        """
        select
            tc.table_name,
            kcu.column_name,
            ccu.table_name as foreign_table_name,
            ccu.column_name as foreign_column_name
        from information_schema.table_constraints tc
        join information_schema.key_column_usage kcu
          on tc.constraint_name = kcu.constraint_name
         and tc.table_schema = kcu.table_schema
        join information_schema.constraint_column_usage ccu
          on ccu.constraint_name = tc.constraint_name
         and ccu.table_schema = tc.table_schema
        where tc.constraint_type = 'FOREIGN KEY'
          and tc.table_schema = 'public'
          and (
              tc.table_name like 'dim_%'
              or tc.table_name like 'fact_%'
              or tc.table_name like 'bridge_%'
          )
        order by tc.table_name, kcu.column_name
        """
    )
    return {"relationships": relationships}


@mcp.tool()
def validate_sql(sql: str) -> dict[str, object]:
    """Validate whether SQL is a single read-only PostgreSQL query."""
    return validate_readonly_sql(sql).to_dict()


@mcp.tool()
def run_readonly_sql(sql: str, limit: int = 100) -> dict[str, Any]:
    """Run one safe read-only query against Supabase and cap returned rows."""
    validation = validate_readonly_sql(sql)
    if not validation.is_valid or validation.cleaned_sql is None:
        return {"ok": False, "error": validation.reason, "rows": [], "columns": []}

    try:
        capped_limit = max(1, min(int(limit), 500))
    except (TypeError, ValueError):
        return {"ok": False, "error": "limit must be an integer.", "rows": [], "columns": []}
    wrapped_sql = f"select * from ({validation.cleaned_sql}) as agent_query limit %s"

    try:
        with connect(env_var="BI_AGENT_DB_URL") as conn:
            conn.set_session(readonly=True, autocommit=False)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("set local statement_timeout = %s", (15000,))
                cur.execute(wrapped_sql, (capped_limit,))
                rows = [dict(row) for row in cur.fetchall()]
                columns = [column.name for column in cur.description]
            conn.rollback()
    except Exception as exc:
        return {"ok": False, "error": str(exc), "rows": [], "columns": []}

    return {
        "ok": True,
        "columns": columns,
        "rows": _json_rows(rows),
        "row_count": len(rows),
        "limit": capped_limit,
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
