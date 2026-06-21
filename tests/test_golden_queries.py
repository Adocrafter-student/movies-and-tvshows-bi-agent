import unittest

from netflix_bi_agent.sql_safety import validate_readonly_sql


GOLDEN_QUERIES = [
    (
        "movie_vs_tv_show_counts",
        """
        select ct.type_name, sum(f.title_count) as title_count
        from public.fact_title_catalog f
        join public.dim_content_type ct on ct.content_type_key = f.content_type_key
        group by ct.type_name
        order by title_count desc
        """,
        ["fact_title_catalog", "dim_content_type", "sum(f.title_count)"],
    ),
    (
        "top_countries",
        """
        select c.country_name, count(distinct f.title_catalog_key) as title_count
        from public.fact_title_catalog f
        join public.bridge_catalog_country bcc on bcc.title_catalog_key = f.title_catalog_key
        join public.dim_country c on c.country_key = bcc.country_key
        group by c.country_name
        order by title_count desc
        limit 10
        """,
        ["bridge_catalog_country", "dim_country", "count(distinct f.title_catalog_key)"],
    ),
    (
        "titles_added_by_month",
        """
        select d.year, d.month, d.month_name, sum(f.title_count) as title_count
        from public.fact_title_catalog f
        join public.dim_date_added d on d.date_added_key = f.date_added_key
        group by d.year, d.month, d.month_name
        order by d.year, d.month
        """,
        ["dim_date_added", "d.year", "d.month"],
    ),
    (
        "top_genres_by_content_type",
        """
        select ct.type_name, g.genre_name, count(distinct f.title_catalog_key) as title_count
        from public.fact_title_catalog f
        join public.dim_content_type ct on ct.content_type_key = f.content_type_key
        join public.bridge_catalog_genre bcg on bcg.title_catalog_key = f.title_catalog_key
        join public.dim_genre g on g.genre_key = bcg.genre_key
        group by ct.type_name, g.genre_name
        order by ct.type_name, title_count desc
        """,
        ["bridge_catalog_genre", "dim_genre", "count(distinct f.title_catalog_key)"],
    ),
    (
        "average_movie_duration_by_rating",
        """
        select r.rating, round(avg(f.duration_minutes)::numeric, 1) as avg_duration_minutes
        from public.fact_title_catalog f
        join public.dim_content_type ct on ct.content_type_key = f.content_type_key
        join public.dim_rating r on r.rating_key = f.rating_key
        where ct.type_name = 'Movie'
          and f.duration_minutes is not null
        group by r.rating
        order by avg_duration_minutes desc
        """,
        ["dim_rating", "duration_minutes", "ct.type_name = 'movie'"],
    ),
    (
        "tv_shows_by_seasons_and_rating",
        """
        select r.rating, round(avg(f.seasons_count)::numeric, 1) as avg_seasons
        from public.fact_title_catalog f
        join public.dim_content_type ct on ct.content_type_key = f.content_type_key
        join public.dim_rating r on r.rating_key = f.rating_key
        where ct.type_name = 'TV Show'
          and f.seasons_count is not null
        group by r.rating
        order by avg_seasons desc
        """,
        ["seasons_count", "dim_rating", "ct.type_name = 'tv show'"],
    ),
]


class GoldenQueryTests(unittest.TestCase):
    def test_golden_queries_are_read_only_and_use_expected_tables(self):
        for name, sql, expected_fragments in GOLDEN_QUERIES:
            with self.subTest(name=name):
                validation = validate_readonly_sql(sql)
                self.assertTrue(validation.is_valid, validation.reason)
                lowered_sql = sql.lower()
                for fragment in expected_fragments:
                    self.assertIn(fragment.lower(), lowered_sql)


if __name__ == "__main__":
    unittest.main()
