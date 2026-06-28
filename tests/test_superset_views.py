import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SUPERSET_MIGRATION = PROJECT_ROOT / "migrations" / "003_superset_views.sql"
SUPERSET_DOCKERFILE = PROJECT_ROOT / "docker" / "superset" / "Dockerfile"
DOCKER_COMPOSE = PROJECT_ROOT / "docker-compose.yml"


class SupersetViewMigrationTests(unittest.TestCase):
    def test_superset_view_migration_defines_dashboard_views(self):
        sql = SUPERSET_MIGRATION.read_text(encoding="utf-8").lower()

        expected_views = [
            "public.vw_superset_catalog_titles",
            "public.vw_superset_title_genres",
            "public.vw_superset_title_countries",
            "public.vw_superset_title_people",
        ]
        for view_name in expected_views:
            with self.subTest(view_name=view_name):
                self.assertIn(f"create or replace view {view_name}", sql)

    def test_superset_views_use_fact_centered_bridges(self):
        sql = SUPERSET_MIGRATION.read_text(encoding="utf-8").lower()

        self.assertIn("public.bridge_catalog_genre", sql)
        self.assertIn("public.bridge_catalog_country", sql)
        self.assertIn("public.bridge_catalog_person", sql)
        self.assertNotIn("public.bridge_title_genre", sql)
        self.assertNotIn("public.bridge_title_country", sql)
        self.assertNotIn("public.bridge_title_person", sql)

    def test_superset_docker_setup_exists(self):
        dockerfile = SUPERSET_DOCKERFILE.read_text(encoding="utf-8").lower()
        compose = DOCKER_COMPOSE.read_text(encoding="utf-8").lower()

        self.assertIn("from apache/superset:4.1.1", dockerfile)
        self.assertIn("python -m pip install", dockerfile)
        self.assertIn("psycopg2-binary", dockerfile)
        self.assertIn("8088:8088", compose)
        self.assertIn("superset_secret_key", compose)


if __name__ == "__main__":
    unittest.main()
