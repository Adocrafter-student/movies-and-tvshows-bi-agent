import unittest
from datetime import date

from netflix_bi_agent.etl import normalize_row, parse_date_added, parse_duration, split_multi_value


class EtlParsingTests(unittest.TestCase):
    def test_parse_movie_duration(self):
        self.assertEqual(parse_duration("90 min", "Movie"), (90, None))

    def test_parse_tv_show_duration(self):
        self.assertEqual(parse_duration("2 Seasons", "TV Show"), (None, 2))

    def test_split_multi_value_trims_and_deduplicates(self):
        self.assertEqual(split_multi_value("Dramas, Comedies, dramas,  "), ("Dramas", "Comedies"))

    def test_parse_date_added(self):
        self.assertEqual(parse_date_added(" September 24, 2021 "), date(2021, 9, 24))

    def test_normalize_row_handles_missing_optional_fields(self):
        row = normalize_row(
            {
                "show_id": "s1",
                "type": "Movie",
                "title": "Example Title",
                "director": "",
                "cast": "Actor One, Actor Two",
                "country": "",
                "date_added": "",
                "release_year": "2020",
                "rating": "",
                "duration": "100 min",
                "listed_in": "Documentaries",
                "description": "Example description",
            }
        )

        self.assertEqual(row.show_id, "s1")
        self.assertEqual(row.rating, "Unknown")
        self.assertEqual(row.directors, tuple())
        self.assertEqual(row.cast_members, ("Actor One", "Actor Two"))
        self.assertEqual(row.countries, tuple())
        self.assertIsNone(row.date_added)
        self.assertEqual(row.duration_minutes, 100)
        self.assertIsNone(row.seasons_count)

    def test_normalize_row_recovers_duration_shifted_into_rating(self):
        row = normalize_row(
            {
                "show_id": "s5542",
                "type": "Movie",
                "title": "Louis C.K. 2017",
                "director": "",
                "cast": "",
                "country": "United States",
                "date_added": "April 4, 2017",
                "release_year": "2017",
                "rating": "74 min",
                "duration": "",
                "listed_in": "Movies",
                "description": "Stand-up special",
            }
        )

        self.assertEqual(row.rating, "Unknown")
        self.assertEqual(row.duration_text, "74 min")
        self.assertEqual(row.duration_minutes, 74)


if __name__ == "__main__":
    unittest.main()
