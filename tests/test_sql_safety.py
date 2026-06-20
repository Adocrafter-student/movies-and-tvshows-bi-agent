import unittest

from netflix_bi_agent.sql_safety import validate_readonly_sql


class SqlSafetyTests(unittest.TestCase):
    def test_select_is_allowed(self):
        result = validate_readonly_sql("select title from public.dim_title limit 5;")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.cleaned_sql, "select title from public.dim_title limit 5")

    def test_with_query_is_allowed(self):
        result = validate_readonly_sql(
            """
            with counts as (
                select rating_key, count(*) as title_count
                from public.fact_title_catalog
                group by rating_key
            )
            select * from counts
            """
        )
        self.assertTrue(result.is_valid)

    def test_multiple_statements_are_rejected(self):
        result = validate_readonly_sql("select 1; select 2;")
        self.assertFalse(result.is_valid)
        self.assertIn("Only one SQL statement", result.reason)

    def test_mutation_keywords_are_rejected(self):
        result = validate_readonly_sql("update public.dim_title set title = 'x'")
        self.assertFalse(result.is_valid)
        self.assertIn("Only SELECT or WITH", result.reason)

    def test_select_into_is_rejected(self):
        result = validate_readonly_sql("select * into temp tmp_titles from public.dim_title")
        self.assertFalse(result.is_valid)
        self.assertIn("Forbidden SQL keyword", result.reason)

    def test_for_update_is_rejected(self):
        result = validate_readonly_sql("select * from public.dim_title for update")
        self.assertFalse(result.is_valid)
        self.assertIn("Locking clauses", result.reason)

    def test_keywords_inside_literals_do_not_count(self):
        result = validate_readonly_sql("select 'drop table dim_title' as harmless_text")
        self.assertTrue(result.is_valid)

    def test_final_semicolon_before_trailing_comment_is_cleaned(self):
        result = validate_readonly_sql("select 1 as ok; -- final comment")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.cleaned_sql, "select 1 as ok")


if __name__ == "__main__":
    unittest.main()
