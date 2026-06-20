import os
import unittest


@unittest.skipUnless(os.getenv("BI_AGENT_DB_URL"), "BI_AGENT_DB_URL is not set; skipping Supabase integration tests.")
class McpDatabaseIntegrationTests(unittest.TestCase):
    def test_schema_summary_returns_tables(self):
        from netflix_bi_agent.mcp_server import get_schema_summary

        summary = get_schema_summary()
        table_names = {table["table_name"] for table in summary["tables"]}
        self.assertIn("fact_title_catalog", table_names)

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


if __name__ == "__main__":
    unittest.main()
