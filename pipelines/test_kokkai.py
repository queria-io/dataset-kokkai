import unittest
from datetime import date

from pipelines.kokkai import months, span_to_fetch


class MonthsTest(unittest.TestCase):
    def test_clips_first_and_last_month(self):
        self.assertEqual(
            months(date(2025, 11, 20), date(2026, 1, 5)),
            [(date(2025, 11, 20), date(2025, 11, 30)), (date(2025, 12, 1), date(2025, 12, 31)), (date(2026, 1, 1), date(2026, 1, 5))],
        )


class SpanTest(unittest.TestCase):
    def test_refetches_before_cursor(self):
        self.assertEqual(span_to_fetch(date(2026, 10, 30), date(2026, 11, 12), True), (date(2026, 5, 3), date(2026, 11, 12)))

    def test_first_run_starts_at_first_diet(self):
        start, end = span_to_fetch(None, date(2026, 11, 12), True)
        self.assertEqual(start, date(1947, 5, 20))
        self.assertLess(end, date(1951, 1, 1))


if __name__ == "__main__":
    unittest.main()
