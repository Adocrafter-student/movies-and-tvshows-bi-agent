import os
import unittest


@unittest.skipUnless(os.getenv("BI_AGENT_DB_URL"), "BI_AGENT_DB_URL is not set; skipping Supabase integration tests.")
class McpDatabaseIntegrationTests(unittest.TestCase):
    def test_schema_summary_returns_tables(self):
        from netflix_bi_agent.mcp_server import get_schema_summary

        summary = get_schema_summary()
        table_names = {table["table_name"] for table in summary["tables"]}
        self.assertIn("fact_title_catalog", table_names)
        self.assertIn("bridge_catalog_genre", table_names)
        self.assertIn("bridge_catalog_country", table_names)
        self.assertIn("bridge_catalog_person", table_names)
        self.assertNotIn("bridge_title_genre", table_names)
        self.assertNotIn("bridge_title_country", table_names)
        self.assertNotIn("bridge_title_person", table_names)

    def test_readonly_query_runs(self):
        from netflix_bi_agent.mcp_server import run_readonly_sql

        result = run_readonly_sql("select 1 as ok")
        self.assertTrue(result["ok"])
        self.assertEqual(result["rows"][0]["ok"], 1)

    def test_mutation_is_rejected_before_execution(self):
        from netflix_bi_agent.mcp_server import run_readonly_sql

        result = run_readonly_sql("drop table public.dim_title")
        self.assertFalse(result["ok"])
        self.assertIn("Only SELECT or WITH", result["error"])

    def test_superset_views_return_expected_sanity_counts(self):
        from netflix_bi_agent.mcp_server import run_readonly_sql

        probe = run_readonly_sql("select to_regclass('public.vw_superset_catalog_titles') as view_name")
        self.assertTrue(probe["ok"], probe.get("error"))
        if probe["rows"][0]["view_name"] is None:
            self.skipTest("Superset views are not applied; run migrations/003_superset_views.sql.")

        catalog = run_readonly_sql(
            """
            select
                count(*)::int as total_titles,
                sum(case when content_type = 'Movie' then title_count else 0 end)::int as movies,
                sum(case when content_type = 'TV Show' then title_count else 0 end)::int as tv_shows
            from public.vw_superset_catalog_titles
            """
        )
        self.assertTrue(catalog["ok"], catalog.get("error"))
        self.assertEqual(catalog["rows"][0]["total_titles"], 8807)
        self.assertEqual(catalog["rows"][0]["movies"], 6131)
        self.assertEqual(catalog["rows"][0]["tv_shows"], 2676)

        genres = run_readonly_sql(
            "select count(distinct genre_name)::int as genres from public.vw_superset_title_genres"
        )
        self.assertTrue(genres["ok"], genres.get("error"))
        self.assertEqual(genres["rows"][0]["genres"], 42)

        countries = run_readonly_sql(
            "select count(distinct country_name)::int as countries from public.vw_superset_title_countries"
        )
        self.assertTrue(countries["ok"], countries.get("error"))
        self.assertEqual(countries["rows"][0]["countries"], 122)


if __name__ == "__main__":
    unittest.main()
