from __future__ import annotations

import argparse
import logging
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

from .config import DEFAULT_DATASET_PATH


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


@dataclass(frozen=True)
class NetflixTitle:
    show_id: str
    content_type: str
    title: str
    directors: tuple[str, ...]
    cast_members: tuple[str, ...]
    countries: tuple[str, ...]
    date_added: date | None
    release_year: int | None
    rating: str
    duration_text: str | None
    duration_minutes: int | None
    seasons_count: int | None
    genres: tuple[str, ...]
    description: str | None


def clean_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return None
    return text


def parse_int(value: object) -> int | None:
    text = clean_text(value)
    if text is None:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def split_multi_value(value: object) -> tuple[str, ...]:
    text = clean_text(value)
    if text is None:
        return tuple()

    seen: set[str] = set()
    values: list[str] = []
    for item in text.split(","):
        cleaned = clean_text(item)
        if cleaned is None:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        values.append(cleaned)
    return tuple(values)


def parse_date_added(value: object) -> date | None:
    text = clean_text(value)
    if text is None:
        return None

    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_duration(duration: object, content_type: object = None) -> tuple[int | None, int | None]:
    text = clean_text(duration)
    if text is None:
        return None, None

    match = re.search(r"\d+", text)
    if not match:
        return None, None

    amount = int(match.group(0))
    duration_lc = text.lower()
    type_lc = (clean_text(content_type) or "").lower()

    if "season" in duration_lc or type_lc == "tv show":
        return None, amount
    if "min" in duration_lc or type_lc == "movie":
        return amount, None
    return None, None


def normalize_row(raw: dict[str, object]) -> NetflixTitle:
    show_id = clean_text(raw.get("show_id"))
    if show_id is None:
        raise ValueError("Netflix row is missing show_id")

    content_type = clean_text(raw.get("type")) or "Unknown"
    rating = clean_text(raw.get("rating")) or "Unknown"
    duration_text = clean_text(raw.get("duration"))
    if duration_text is None and rating != "Unknown" and parse_duration(rating, content_type) != (None, None):
        duration_text = rating
        rating = "Unknown"
    duration_minutes, seasons_count = parse_duration(duration_text, content_type)

    return NetflixTitle(
        show_id=show_id,
        content_type=content_type,
        title=clean_text(raw.get("title")) or "Untitled",
        directors=split_multi_value(raw.get("director")),
        cast_members=split_multi_value(raw.get("cast")),
        countries=split_multi_value(raw.get("country")),
        date_added=parse_date_added(raw.get("date_added")),
        release_year=parse_int(raw.get("release_year")),
        rating=rating,
        duration_text=duration_text,
        duration_minutes=duration_minutes,
        seasons_count=seasons_count,
        genres=split_multi_value(raw.get("listed_in")),
        description=clean_text(raw.get("description")),
    )


def load_netflix_csv(path: str | Path = DEFAULT_DATASET_PATH) -> list[NetflixTitle]:
    import pandas as pd

    csv_path = Path(path)
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    df = df.drop_duplicates(subset=["show_id"], keep="first")
    return [normalize_row(row) for row in df.to_dict("records")]


def _execute_values(cur, query: str, rows: Iterable[tuple], page_size: int = 1000) -> None:
    rows = list(rows)
    if not rows:
        return

    from psycopg2.extras import execute_values

    execute_values(cur, query, rows, page_size=page_size)


def _upsert_lookup(cur, table_name: str, key_column: str, value_column: str, values: Iterable[str]) -> dict[str, int]:
    unique_values = sorted({value for value in values if value})
    _execute_values(
        cur,
        f"""
        insert into public.{table_name} ({value_column})
        values %s
        on conflict ({value_column}) do nothing
        """,
        [(value,) for value in unique_values],
    )
    cur.execute(f"select {key_column}, {value_column} from public.{table_name}")
    return {value: key for key, value in cur.fetchall()}


def _upsert_dates(cur, rows: list[NetflixTitle]) -> dict[date, int]:
    dates = sorted({row.date_added for row in rows if row.date_added is not None})
    date_rows = [
        (
            item,
            item.year,
            item.month,
            item.strftime("%B"),
            ((item.month - 1) // 3) + 1,
            item.day,
            item.weekday(),
            item.strftime("%A"),
        )
        for item in dates
    ]
    _execute_values(
        cur,
        """
        insert into public.dim_date_added
            (full_date, year, month, month_name, quarter, day, day_of_week, day_name)
        values %s
        on conflict (full_date) do nothing
        """,
        date_rows,
    )
    cur.execute("select date_added_key, full_date from public.dim_date_added")
    return {full_date: date_added_key for date_added_key, full_date in cur.fetchall()}


def _upsert_titles(cur, rows: list[NetflixTitle]) -> dict[str, int]:
    _execute_values(
        cur,
        """
        insert into public.dim_title
            (show_id, title, description, release_year, duration_text, duration_minutes, seasons_count)
        values %s
        on conflict (show_id) do update set
            title = excluded.title,
            description = excluded.description,
            release_year = excluded.release_year,
            duration_text = excluded.duration_text,
            duration_minutes = excluded.duration_minutes,
            seasons_count = excluded.seasons_count,
            updated_at = now()
        """,
        [
            (
                row.show_id,
                row.title,
                row.description,
                row.release_year,
                row.duration_text,
                row.duration_minutes,
                row.seasons_count,
            )
            for row in rows
        ],
    )
    cur.execute("select title_key, show_id from public.dim_title")
    return {show_id: title_key for title_key, show_id in cur.fetchall()}


def _refresh_bridges(
    cur,
    rows: list[NetflixTitle],
    catalog_map: dict[str, int],
    genre_map: dict[str, int],
    country_map: dict[str, int],
    person_map: dict[str, int],
) -> None:
    catalog_keys = [catalog_map[row.show_id] for row in rows]
    if not catalog_keys:
        return

    cur.execute("delete from public.bridge_catalog_genre where title_catalog_key = any(%s)", (catalog_keys,))
    cur.execute("delete from public.bridge_catalog_country where title_catalog_key = any(%s)", (catalog_keys,))
    cur.execute("delete from public.bridge_catalog_person where title_catalog_key = any(%s)", (catalog_keys,))

    genre_rows: list[tuple[int, int]] = []
    country_rows: list[tuple[int, int]] = []
    person_rows: list[tuple[int, int, str]] = []

    for row in rows:
        title_catalog_key = catalog_map[row.show_id]
        genre_rows.extend((title_catalog_key, genre_map[genre]) for genre in row.genres)
        country_rows.extend((title_catalog_key, country_map[country]) for country in row.countries)
        person_rows.extend((title_catalog_key, person_map[person], "director") for person in row.directors)
        person_rows.extend((title_catalog_key, person_map[person], "cast") for person in row.cast_members)

    _execute_values(
        cur,
        """
        insert into public.bridge_catalog_genre (title_catalog_key, genre_key)
        values %s
        on conflict do nothing
        """,
        genre_rows,
    )
    _execute_values(
        cur,
        """
        insert into public.bridge_catalog_country (title_catalog_key, country_key)
        values %s
        on conflict do nothing
        """,
        country_rows,
    )
    _execute_values(
        cur,
        """
        insert into public.bridge_catalog_person (title_catalog_key, person_key, role)
        values %s
        on conflict do nothing
        """,
        person_rows,
    )


def _upsert_fact(
    cur,
    rows: list[NetflixTitle],
    title_map: dict[str, int],
    content_type_map: dict[str, int],
    rating_map: dict[str, int],
    date_map: dict[date, int],
) -> dict[str, int]:
    fact_rows = []
    for row in rows:
        type_lc = row.content_type.lower()
        fact_rows.append(
            (
                title_map[row.show_id],
                content_type_map[row.content_type],
                rating_map[row.rating],
                date_map.get(row.date_added) if row.date_added else None,
                row.release_year,
                1,
                type_lc == "movie",
                type_lc == "tv show",
                row.duration_minutes,
                row.seasons_count,
            )
        )

    _execute_values(
        cur,
        """
        insert into public.fact_title_catalog
            (title_key, content_type_key, rating_key, date_added_key, release_year,
             title_count, movie_flag, tv_show_flag, duration_minutes, seasons_count)
        values %s
        on conflict (title_key) do update set
            content_type_key = excluded.content_type_key,
            rating_key = excluded.rating_key,
            date_added_key = excluded.date_added_key,
            release_year = excluded.release_year,
            title_count = excluded.title_count,
            movie_flag = excluded.movie_flag,
            tv_show_flag = excluded.tv_show_flag,
            duration_minutes = excluded.duration_minutes,
            seasons_count = excluded.seasons_count,
            loaded_at = now()
        """,
        fact_rows,
    )

    cur.execute(
        """
        select fact.title_catalog_key, title.show_id
        from public.fact_title_catalog fact
        join public.dim_title title on title.title_key = fact.title_key
        """
    )
    return {show_id: title_catalog_key for title_catalog_key, show_id in cur.fetchall()}


def run_etl(csv_path: str | Path = DEFAULT_DATASET_PATH, database_url: str | None = None) -> dict[str, int]:
    rows = load_netflix_csv(csv_path)
    logging.info("Loaded %s Netflix rows from %s", len(rows), csv_path)

    all_genres = [genre for row in rows for genre in row.genres]
    all_countries = [country for row in rows for country in row.countries]
    all_people = [person for row in rows for person in row.directors + row.cast_members]

    from .db import connect

    with connect(database_url, env_var="SUPABASE_DB_URL") as conn:
        with conn.cursor() as cur:
            content_type_map = _upsert_lookup(
                cur,
                "dim_content_type",
                "content_type_key",
                "type_name",
                [row.content_type for row in rows],
            )
            rating_map = _upsert_lookup(cur, "dim_rating", "rating_key", "rating", [row.rating for row in rows])
            genre_map = _upsert_lookup(cur, "dim_genre", "genre_key", "genre_name", all_genres)
            country_map = _upsert_lookup(cur, "dim_country", "country_key", "country_name", all_countries)
            person_map = _upsert_lookup(cur, "dim_person", "person_key", "person_name", all_people)
            date_map = _upsert_dates(cur, rows)
            title_map = _upsert_titles(cur, rows)

            catalog_map = _upsert_fact(cur, rows, title_map, content_type_map, rating_map, date_map)
            _refresh_bridges(cur, rows, catalog_map, genre_map, country_map, person_map)

        conn.commit()

    result = {
        "titles": len(rows),
        "genres": len(set(all_genres)),
        "countries": len(set(all_countries)),
        "people": len(set(all_people)),
    }
    logging.info("Netflix ETL completed: %s", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Load netflix_titles.csv into the Supabase BI schema.")
    parser.add_argument("--csv", default=str(DEFAULT_DATASET_PATH), help="Path to netflix_titles.csv.")
    args = parser.parse_args()
    run_etl(args.csv)


if __name__ == "__main__":
    main()
