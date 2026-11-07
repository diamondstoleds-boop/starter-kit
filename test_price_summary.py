"""Checks for price_summary.py."""

import unittest

from price_summary import PriceDataError, summarize_prices


def row(date, close, high=None, low=None, volume=1000):
    return {"symbol": "BBCA.JK", "date": date, "close": close,
            "high": close if high is None else high,
            "low": close if low is None else low, "volume": volume}


ROWS = [
    row("2026-11-04", 5000, high=5300, low=4900, volume=100),
    row("2026-11-05", 5125, high=5150, low=5000, volume=200),
    row("2026-11-06", 5200, high=5225, low=5100, volume=300),
]


class TestSummarizePrices(unittest.TestCase):
    def test_known_prices_give_known_summary(self):
        self.assertEqual(
            summarize_prices("BBCA", ROWS),
            {
                "ticker": "BBCA",
                "last_close": 5200,
                "close_date": "2026-11-06",
                "daily_change": (5200 - 5125) / 5125,
                "high_30d": 5300,
                "low_30d": 4900,
                "volume": 300,
            },
        )

    def test_rows_out_of_order_give_same_result(self):
        shuffled = [ROWS[2], ROWS[0], ROWS[1]]
        self.assertEqual(summarize_prices("BBCA", shuffled), summarize_prices("BBCA", ROWS))

    def test_one_day_of_data_has_no_daily_change(self):
        summary = summarize_prices("BBCA", [ROWS[2]])
        self.assertIsNone(summary["daily_change"])
        self.assertEqual(summary["last_close"], 5200)

    def test_empty_rows_raise(self):
        with self.assertRaises(PriceDataError):
            summarize_prices("BBCA", [])

    def test_missing_field_raises(self):
        broken = dict(ROWS[2])
        del broken["close"]
        with self.assertRaises(PriceDataError):
            summarize_prices("BBCA", [ROWS[0], broken])

    def test_non_numeric_close_raises(self):
        with self.assertRaises(PriceDataError):
            summarize_prices("BBCA", [row("2026-11-06", None)])

    def test_text_close_raises(self):
        with self.assertRaises(PriceDataError):
            summarize_prices("BBCA", [row("2026-11-06", "5200")])

    def test_bad_date_raises(self):
        with self.assertRaises(PriceDataError):
            summarize_prices("BBCA", [row("Nov 6", 5200)])

    def test_zero_previous_close_has_no_daily_change(self):
        summary = summarize_prices("BBCA", [row("2026-11-05", 0), row("2026-11-06", 5200)])
        self.assertIsNone(summary["daily_change"])

    def test_row_that_is_not_a_dict_raises(self):
        with self.assertRaises(PriceDataError):
            summarize_prices("BBCA", ["oops"])


if __name__ == "__main__":
    unittest.main()
