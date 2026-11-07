"""Checks for a full run of daily_report.py. No test touches the real network."""

import contextlib
import io
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

import requests

import daily_report
import fetch_daily_prices as fdp

FAKE_KEY = "fake-key-do-not-leak-123"
MONDAY_0730_WIB = datetime(2026, 11, 9, 7, 30, 4, tzinfo=ZoneInfo("Asia/Jakarta"))
GOOD_ROWS = [{"symbol": "X.JK", "date": "2026-11-06", "close": 5200, "high": 5225,
              "low": 5100, "volume": 300}]
CSV = ("month,cash_in,cash_out,net_cash_flow,ending_balance\n"
       "2026-10,1100000000,860000000,240000000,3330000000\n")


def fake_response(body=GOOD_ROWS, status=200):
    response = mock.Mock(status_code=status)
    response.json.return_value = body
    return response


class RunTestCase(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.reports = self.root / "reports"
        self.log = self.root / "logs" / "daily_report.log"
        self.csv = self.root / "cash.csv"
        self.csv.write_text(CSV)
        self.screen = io.StringIO()

    def run_report(self, get=None, now=MONDAY_0730_WIB, environ=None):
        """Run the report. `get` maps a ticker to the fake API's answer."""
        answers = get or {}

        def fake_get(url, **_kwargs):
            ticker = url.rstrip("/").rsplit("/", 1)[-1]
            answer = answers.get(ticker, fake_response())
            if isinstance(answer, Exception):
                raise answer
            return answer

        with mock.patch.object(fdp.requests, "get", side_effect=fake_get):
            with contextlib.redirect_stdout(self.screen):
                return daily_report.run_daily_report(
                    now=now,
                    reports_dir=self.reports,
                    log_path=self.log,
                    data_dir=self.root / "data",
                    cash_flow_path=self.csv,
                    env_path=self.root / ".env",
                    environ={"SECTORS_API_KEY": FAKE_KEY} if environ is None else environ,
                )

    def log_lines(self):
        return self.log.read_text().splitlines()

    def report(self, name="2026-11-09.md"):
        return (self.reports / name).read_text()


class TestRun(RunTestCase):
    def test_all_banks_saved_and_logged_as_ok(self):
        self.assertEqual(self.run_report(), 0)
        for ticker in ("BBCA", "BBRI", "BMRI", "NISP"):
            self.assertIn(f"| {ticker} |", self.report())
            self.assertTrue((self.root / "data" / f"daily_{ticker}.json").exists())
        self.assertEqual(
            self.log_lines(),
            ["2026-11-09T07:30:04+07:00 status=ok included=BBCA,BBRI,BMRI,NISP "
             "not_included=none cash_flow=ok report=reports/2026-11-09.md"],
        )

    def test_one_failed_ticker_still_saves_report_and_succeeds(self):
        code = self.run_report({"NISP": fake_response({"error": "x"}, 429)})
        self.assertEqual(code, 0)
        self.assertIn("- NISP: price request failed (HTTP 429)\n", self.report())
        self.assertIn("| BBCA |", self.report())
        self.assertIn(" status=partial included=BBCA,BBRI,BMRI not_included=NISP ",
                      self.log_lines()[0])

    def test_bad_price_rows_put_ticker_under_not_included(self):
        code = self.run_report({"BBRI": fake_response([{"date": "2026-11-06"}])})
        self.assertEqual(code, 0)
        self.assertIn("- BBRI: invalid price data\n", self.report())

    def test_unexpected_error_for_one_ticker_does_not_stop_the_others(self):
        with mock.patch.object(daily_report, "summarize_prices",
                               side_effect=[RuntimeError(FAKE_KEY)] + [
                                   {"ticker": t, "last_close": 1, "close_date": "2026-11-06",
                                    "daily_change": None, "high_30d": 1, "low_30d": 1, "volume": 1}
                                   for t in ("BBRI", "BMRI", "NISP")]):
            self.assertEqual(self.run_report(), 0)
        self.assertIn("- BBCA: unexpected error (RuntimeError)\n", self.report())
        self.assertIn("| NISP |", self.report())

    def test_all_failed_still_saves_report_and_exits_as_failure(self):
        error = requests.ConnectionError("down")
        code = self.run_report({t: error for t in ("BBCA", "BBRI", "BMRI", "NISP")})
        self.assertEqual(code, 1)
        self.assertIn("No bank prices available.", self.report())
        self.assertIn(" status=failed included=none not_included=BBCA,BBRI,BMRI,NISP ",
                      self.log_lines()[0])

    def test_missing_key_saves_report_and_exits_as_failure(self):
        code = self.run_report(environ={})
        self.assertEqual(code, 1)
        self.assertIn("- BBCA: price request failed (SECTORS_API_KEY is not set)\n", self.report())
        self.assertEqual(len(self.log_lines()), 1)

    def test_missing_cash_flow_is_partial_but_succeeds(self):
        self.csv.unlink()
        self.assertEqual(self.run_report(), 0)
        self.assertIn("Not available: cash flow file could not be read", self.report())
        self.assertIn(" status=partial ", self.log_lines()[0])
        self.assertIn(" cash_flow=missing ", self.log_lines()[0])

    def test_report_that_cannot_be_saved_is_still_logged_as_failed(self):
        self.reports.write_text("a file is in the way")
        self.assertEqual(self.run_report(), 1)
        self.assertIn(" status=failed ", self.log_lines()[0])
        self.assertTrue(self.log_lines()[0].endswith(" report=not_saved"))

    def test_date_in_filename_is_wib_not_utc(self):
        sunday_evening_utc = datetime(2026, 11, 8, 18, 0, tzinfo=timezone.utc)
        self.run_report(now=sunday_evening_utc)
        self.assertTrue((self.reports / "2026-11-09.md").exists())
        self.assertTrue(self.log_lines()[0].startswith("2026-11-09T01:00:00+07:00 "))

    def test_second_run_replaces_report_and_adds_log_line(self):
        self.run_report({"NISP": fake_response({}, 500)})
        self.run_report()
        self.assertEqual(len(list(self.reports.iterdir())), 1)
        self.assertIn("| NISP |", self.report())
        self.assertEqual(len(self.log_lines()), 2)

    def test_key_never_appears_in_report_log_or_screen(self):
        self.run_report({"BBCA": requests.ConnectionError(f"boom {FAKE_KEY}"),
                         "BBRI": fake_response({"error": FAKE_KEY}, 401)})
        self.assertNotIn(FAKE_KEY, self.report())
        self.assertNotIn(FAKE_KEY, self.log.read_text())
        self.assertNotIn(FAKE_KEY, self.screen.getvalue())


if __name__ == "__main__":
    unittest.main()
