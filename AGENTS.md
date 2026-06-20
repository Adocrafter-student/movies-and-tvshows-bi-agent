# AGENTS.md

## Project Purpose

This repository is a Netflix Movies and TV Shows BI agent project. The canonical dataset is `datasets/netflix_titles.csv`; Online Retail files are legacy professor boilerplate only.

## Database

- Target database: Supabase PostgreSQL.
- Migration entrypoint: `python -m netflix_bi_agent.apply_migration`.
- ETL entrypoint: `python -m netflix_bi_agent.etl`.
- MCP entrypoint: `python -m netflix_bi_agent.mcp_server`.
- Keep secrets in `.env`; never commit database URLs or passwords.

## BI Agent SQL Rules

- Inspect schema before writing SQL.
- Use PostgreSQL syntax.
- Generate only read-only `SELECT` or `WITH` queries.
- Use `fact_title_catalog` as the central fact table.
- Use bridge tables for multi-value fields: genres, countries, directors, and cast.
- Return the SQL and a short business interpretation of the result.

## Verification

- Run `python -m unittest discover` after changing ETL, SQL safety, or MCP code.
- Run `python -m compileall netflix_bi_agent` after changing package code.
