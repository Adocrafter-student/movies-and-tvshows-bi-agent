from __future__ import annotations

from typing import Any

from .config import get_required_env


def connect(database_url: str | None = None, *, env_var: str = "SUPABASE_DB_URL") -> Any:
    """Create a psycopg2 connection from an explicit URL or environment variable."""
    import psycopg2

    return psycopg2.connect(database_url or get_required_env(env_var))
