from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET_PATH = PROJECT_ROOT / "datasets" / "netflix_titles.csv"
DEFAULT_MIGRATION_PATH = PROJECT_ROOT / "migrations" / "001_netflix_schema.sql"


def load_project_env() -> None:
    """Load local environment variables when a .env file exists."""
    load_dotenv(PROJECT_ROOT / ".env")


def get_required_env(name: str) -> str:
    load_project_env()
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value
