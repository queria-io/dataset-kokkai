import unittest
from datetime import date

import tempfile
from pathlib import Path

from pipelines.kokkai import already_fetched, months, span_to_fetch


class MonthsTest(unittest.TestCase):
    def test_clips_first_and_last_month(self):
        self.assertEqual(
            months(date(2025, 11, 20), date(2026, 1, 5)),
            [(date(2025, 11, 20), date(2025, 11, 30)), (date(2025, 12, 1), date(2025, 12, 31)), (date(2026, 1, 1), date(2026, 1, 5))],
        )


class AlreadyFetchedTest(unittest.TestCase):
    def test_skips_old_month_with_file_but_refetches_recent(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            (out / "1955-06.ndjson.gz").touch()
            (out / "2026-10.ndjson.gz").touch()
            today = date(2026, 11, 13)
            self.assertTrue(already_fetched(date(1955, 6, 1), date(1955, 6, 30), today, out))
            self.assertFalse(already_fetched(date(1955, 7, 1), date(1955, 7, 31), today, out))
            self.assertFalse(already_fetched(date(2026, 10, 1), date(2026, 10, 31), today, out))


class SpanTest(unittest.TestCase):
    def test_refetches_before_cursor(self):
        self.assertEqual(span_to_fetch(date(2026, 10, 30), date(2026, 11, 12), True), (date(2026, 5, 3), date(2026, 11, 12)))

    def test_backfill_continues_from_cursor(self):
        start, _ = span_to_fetch(date(1960, 3, 4), date(2026, 11, 12), True)
        self.assertEqual(start, date(1960, 3, 4))

    def test_first_run_starts_at_first_diet(self):
        start, end = span_to_fetch(None, date(2026, 11, 12), True)
        self.assertEqual(start, date(1947, 5, 20))
        self.assertLess(end, date(1951, 1, 1))


if __name__ == "__main__":
    unittest.main()
