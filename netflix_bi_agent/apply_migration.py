from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .config import DEFAULT_MIGRATION_PATH
from .db import connect


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def apply_migration(path: str | Path = DEFAULT_MIGRATION_PATH, database_url: str | None = None) -> None:
    migration_path = Path(path)
    sql = migration_path.read_text(encoding="utf-8")

    with connect(database_url, env_var="SUPABASE_DB_URL") as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()

    logging.info("Applied migration: %s", migration_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply the Netflix BI Supabase schema migration.")
    parser.add_argument("--path", default=str(DEFAULT_MIGRATION_PATH), help="Path to SQL migration file.")
    args = parser.parse_args()
    apply_migration(args.path)


if __name__ == "__main__":
    main()
