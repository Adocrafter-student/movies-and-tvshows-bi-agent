# Netflix Movies and TV Shows BI Agent

This project implements Phase 2 of the BI Agent assignment around the Netflix Movies and TV Shows dataset. It uses Supabase PostgreSQL for the warehouse, a Python ETL pipeline for ingestion, and a FastMCP server so Codex CLI can inspect the schema and run safe read-only SQL.

The canonical project dataset is `datasets/netflix_titles.csv`.

## Project Structure

- `datasets/netflix_titles.csv`: source dataset.
- `migrations/001_netflix_schema.sql`: fresh Supabase PostgreSQL warehouse schema.
- `migrations/002_fact_centered_bridges.sql`: existing-database migration for the fact-centered bridge refactor.
- `netflix_bi_agent/etl.py`: idempotent Netflix CSV ingestion.
- `netflix_bi_agent/mcp_server.py`: Codex MCP server.
- `netflix_bi_agent/sql_safety.py`: read-only SQL validation.
- `docs/bi_agent_system_instructions.md`: prompt engineering deliverable.
- `docs/golden_queries.md`: evaluation questions and expected SQL patterns.
- `.codex/config.toml`: project-scoped Codex MCP configuration.

## Warehouse Design

The warehouse uses one row per Netflix title in `fact_title_catalog`.

Dimensions:

- `dim_title`
- `dim_content_type`
- `dim_rating`
- `dim_date_added`
- `dim_genre`
- `dim_country`
- `dim_person`

Bridge tables:

- `bridge_catalog_genre`
- `bridge_catalog_country`
- `bridge_catalog_person`

The bridge tables normalize CSV columns that contain comma-separated values, such as genres, countries, directors, and cast members.

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Create a Supabase project and copy the PostgreSQL connection string from the Supabase dashboard.

3. Create `.env` from `.env.example`:

```env
SUPABASE_DB_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres?sslmode=require
BI_AGENT_DB_URL=postgresql://bi_agent_reader:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres?sslmode=require
```

4. Apply the schema migration for a fresh Supabase database:

```bash
python -m netflix_bi_agent.apply_migration
```

For an existing database that already had the earlier title-centered bridge tables, apply the follow-up migration once:

```bash
python -m netflix_bi_agent.apply_migration --path migrations/002_fact_centered_bridges.sql
```

5. Load or reload the Netflix dataset:

```bash
python -m netflix_bi_agent.etl
```

## Read-Only Agent Role

Use a dedicated read-only role for `BI_AGENT_DB_URL` when possible:

```sql
create role bi_agent_reader with login password 'replace-with-strong-password';
grant usage on schema public to bi_agent_reader;
grant select on all tables in schema public to bi_agent_reader;
alter default privileges in schema public grant select on tables to bi_agent_reader;
```

If you are using Supabase connection poolers, use the session pooler for long-lived MCP sessions. For serverless/short-lived jobs, transaction pooler can work, but prepared statements may need to be disabled depending on the client.

## Codex MCP Setup

This repo includes `.codex/config.toml`:

```toml
[mcp_servers.netflix_bi]
command = "python"
args = ["-m", "netflix_bi_agent.mcp_server"]
env_vars = ["BI_AGENT_DB_URL"]
startup_timeout_sec = 20
tool_timeout_sec = 60
```

After setting `BI_AGENT_DB_URL`, restart Codex from the repository root. In Codex CLI, use `/mcp` to confirm the `netflix_bi` server is active.

The server exposes these tools:

- `get_schema_summary`
- `describe_table`
- `get_relationships`
- `validate_sql`
- `run_readonly_sql`

## Agent Rules

The full system instructions are in `docs/bi_agent_system_instructions.md`. In short, the agent should inspect the schema, generate PostgreSQL read-only SQL, use bridge tables for multi-value fields, and return both SQL and a concise business interpretation.

## Verification

Run local tests:

```bash
python -m unittest discover
python -m compileall netflix_bi_agent
```

Database integration tests are skipped unless `BI_AGENT_DB_URL` is set.

## Legacy Boilerplate

The files `OnlineRetail.csv`, `etl_process.py`, `etl_process2.py`, and `product_search.txt` came from the original boilerplate flow. They are not part of the Netflix-first Phase 2 implementation.
