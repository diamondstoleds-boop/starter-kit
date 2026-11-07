"""Checks for the Markdown written by render_report in daily_report.py."""

import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from daily_report import render_report

WHEN = datetime(2026, 11, 9, 7, 30, tzinfo=ZoneInfo("Asia/Jakarta"))


def bank(ticker="BBCA", change=75 / 5125):
    return {"ticker": ticker, "last_close": 5200, "close_date": "2026-11-06",
            "daily_change": change, "high_30d": 6850, "low_30d": 4740,
            "volume": 92219000}


CASH = {"month": "2026-10", "cash_in": 1100000000, "cash_out": 860000000,
        "net_cash_flow": 240000000, "ending_balance": 3330000000, "warnings": []}


class TestRenderReport(unittest.TestCase):
    def test_full_report_has_exact_layout(self):
        self.assertEqual(
            render_report(WHEN, [bank()], {}, CASH, None),
            "# Daily Report: 2026-11-09 (07:30 WIB)\n"
            "\n"
            "## Bank prices\n"
            "| Ticker | Last close (Rp) | Close date | Daily change | 30-day high (Rp) | 30-day low (Rp) | Volume |\n"
            "|---|---|---|---|---|---|---|\n"
            "| BBCA | 5,200 | 2026-11-06 | +1.46% | 6,850 | 4,740 | 92,219,000 |\n"
            "\n"
            "## Company cash flow (through 2026-10)\n"
            "- Cash in: Rp 1,100,000,000\n"
            "- Cash out: Rp 860,000,000\n"
            "- Net cash flow: Rp 240,000,000\n"
            "- Ending balance: Rp 3,330,000,000\n"
            "\n"
            "## Not included\n"
            "None\n",
        )

    def test_failed_bank_moves_from_table_to_not_included(self):
        report = render_report(
            WHEN, [bank("BBCA")], {"NISP": "price request failed (HTTP 429)"}, CASH, None)
        self.assertIn("- NISP: price request failed (HTTP 429)\n", report)
        self.assertNotIn("| NISP |", report)
        self.assertIn("| BBCA |", report)
        self.assertNotIn("None\n", report)

    def test_negative_change_is_shown_with_minus(self):
        self.assertIn("| -0.50% |", render_report(WHEN, [bank(change=-0.005)], {}, CASH, None))

    def test_unknown_change_says_not_available(self):
        self.assertIn("| not available |", render_report(WHEN, [bank(change=None)], {}, CASH, None))

    def test_negative_net_is_shown_with_minus_before_rupiah(self):
        report = render_report(WHEN, [bank()], {}, {**CASH, "net_cash_flow": -30000000}, None)
        self.assertIn("- Net cash flow: -Rp 30,000,000\n", report)

    def test_missing_cash_flow_says_so_and_keeps_prices(self):
        report = render_report(WHEN, [bank()], {}, None, "cash flow file could not be read")
        self.assertIn("## Company cash flow\nNot available: cash flow file could not be read\n", report)
        self.assertIn("| BBCA |", report)

    def test_cash_flow_warning_is_shown(self):
        report = render_report(WHEN, [bank()], {}, {**CASH, "warnings": ["Check this."]}, None)
        self.assertIn("- Warning: Check this.\n", report)

    def test_no_banks_says_so_instead_of_empty_table(self):
        report = render_report(WHEN, [], {"BBCA": "price request failed (HTTP 500)"}, CASH, None)
        self.assertIn("## Bank prices\nNo bank prices available.\n", report)
        self.assertNotIn("| Ticker |", report)

    def test_report_never_gives_trading_advice(self):
        report = render_report(WHEN, [bank()], {"NISP": "x"}, CASH, None).lower()
        for word in ("buy", "sell", "hold"):
            self.assertNotIn(word, report)


if __name__ == "__main__":
    unittest.main()
