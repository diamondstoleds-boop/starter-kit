"""Checks for fetch_daily_prices.py. No test touches the real network."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import requests

import fetch_daily_prices as fdp

FAKE_KEY = "fake-key-do-not-leak-123"
ROWS = [
    {"symbol": "BBCA.JK", "date": "2026-11-05", "close": 5125, "open": 5100,
     "high": 5150, "low": 5075, "volume": 1000, "market_cap": 1},
    {"symbol": "BBCA.JK", "date": "2026-11-06", "close": 5200, "open": 5125,
     "high": 5225, "low": 5100, "volume": 2000, "market_cap": 1},
]


def response(status=200, body=ROWS):
    fake = mock.Mock()
    fake.status_code = status
    fake.json.return_value = body
    return fake


class FetchTestCase(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.data_dir = Path(folder.name)
        self.saved = self.data_dir / "daily_BBCA.json"


class TestRequest(FetchTestCase):
    @mock.patch.object(fdp.requests, "get", return_value=response())
    def test_calls_daily_address_with_key_in_header(self, get):
        fdp.fetch_daily_prices("BBCA", FAKE_KEY, self.data_dir)
        args, kwargs = get.call_args
        self.assertEqual(args[0], "https://api.sectors.app/v2/daily/BBCA/")
        self.assertEqual(kwargs["headers"], {"Authorization": FAKE_KEY})
        self.assertGreater(kwargs["timeout"], 0)


class TestSaving(FetchTestCase):
    @mock.patch.object(fdp.requests, "get", return_value=response())
    def test_saves_valid_rows_to_daily_ticker_file(self, _get):
        rows = fdp.fetch_daily_prices("BBCA", FAKE_KEY, self.data_dir)
        self.assertEqual(rows, ROWS)
        self.assertEqual(json.loads(self.saved.read_text()), ROWS)
        self.assertNotIn(FAKE_KEY, self.saved.read_text())

    def assert_fails_and_keeps_last_good_file(self, expected_reason, **get_kwargs):
        self.saved.write_text('"last good"')
        with mock.patch.object(fdp.requests, "get", **get_kwargs):
            with self.assertRaises(fdp.FetchError) as caught:
                fdp.fetch_daily_prices("BBCA", FAKE_KEY, self.data_dir)
        self.assertEqual(str(caught.exception), expected_reason)
        self.assertEqual(self.saved.read_text(), '"last good"')

    def test_http_error_keeps_last_good_file(self):
        self.assert_fails_and_keeps_last_good_file(
            "HTTP 429", return_value=response(429, {"error": "RATE_LIMIT_EXCEEDED"}))

    def test_empty_list_keeps_last_good_file(self):
        self.assert_fails_and_keeps_last_good_file(
            "no price data returned", return_value=response(200, []))

    def test_non_list_body_keeps_last_good_file(self):
        self.assert_fails_and_keeps_last_good_file(
            "unexpected response", return_value=response(200, {"error": "x"}))

    def test_invalid_json_keeps_last_good_file(self):
        bad = response()
        bad.json.side_effect = ValueError("not json")
        self.assert_fails_and_keeps_last_good_file(
            "unexpected response", return_value=bad)

    def test_network_error_message_hides_exception_text(self):
        self.assert_fails_and_keeps_last_good_file(
            "network error (ConnectionError)",
            side_effect=requests.ConnectionError(f"boom {FAKE_KEY}"))


class TestApiKey(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.env_path = Path(folder.name) / ".env"

    def test_environment_is_used_first(self):
        self.env_path.write_text("SECTORS_API_KEY=from-file\n")
        key = fdp.get_api_key(self.env_path, {"SECTORS_API_KEY": "from-environment"})
        self.assertEqual(key, "from-environment")

    def test_falls_back_to_env_file_and_strips_quotes(self):
        self.env_path.write_text('# note\nSECTORS_API_KEY="from-file"\n')
        self.assertEqual(fdp.get_api_key(self.env_path, {}), "from-file")

    def test_missing_key_raises_fetch_error(self):
        with self.assertRaises(fdp.FetchError) as caught:
            fdp.get_api_key(self.env_path, {})
        self.assertEqual(str(caught.exception), "SECTORS_API_KEY is not set")


if __name__ == "__main__":
    unittest.main()
