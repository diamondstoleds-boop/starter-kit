"""Checks for cash_flow.py."""

import tempfile
import unittest
from pathlib import Path

from cash_flow import CashFlowError, summarize_cash_flow

HEADER = "month,cash_in,cash_out,net_cash_flow,ending_balance\n"


class CashFlowTestCase(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "cash.csv"


class TestRealFile(unittest.TestCase):
    def test_sample_file_gives_october_2026_figures(self):
        self.assertEqual(
            summarize_cash_flow(Path(__file__).parent / "data" / "cash_flow_sample.csv"),
            {
                "month": "2026-10",
                "cash_in": 1100000000,
                "cash_out": 860000000,
                "net_cash_flow": 240000000,
                "ending_balance": 3330000000,
                "warnings": [],
            },
        )


class TestSummarizeCashFlow(CashFlowTestCase):
    def test_rows_out_of_order_still_give_true_latest_month(self):
        self.path.write_text(HEADER + "2026-10,30,10,20,120\n2026-09,10,10,0,100\n")
        self.assertEqual(summarize_cash_flow(self.path)["month"], "2026-10")
        self.path.write_text(HEADER + "2026-09,10,10,0,100\n2026-10,30,10,20,120\n")
        self.assertEqual(summarize_cash_flow(self.path)["month"], "2026-10")

    def test_missing_file_raises(self):
        with self.assertRaises(CashFlowError):
            summarize_cash_flow(self.path)

    def test_file_with_no_rows_raises(self):
        self.path.write_text(HEADER)
        with self.assertRaises(CashFlowError):
            summarize_cash_flow(self.path)

    def test_missing_column_raises(self):
        self.path.write_text("month,cash_in\n2026-10,30\n")
        with self.assertRaises(CashFlowError):
            summarize_cash_flow(self.path)

    def test_text_in_number_column_raises(self):
        self.path.write_text(HEADER + "2026-10,abc,10,20,120\n")
        with self.assertRaises(CashFlowError):
            summarize_cash_flow(self.path)

    def test_bad_month_raises(self):
        self.path.write_text(HEADER + "October,30,10,20,120\n")
        with self.assertRaises(CashFlowError):
            summarize_cash_flow(self.path)

    def test_net_that_does_not_add_up_is_flagged(self):
        self.path.write_text(HEADER + "2026-10,30,10,99,120\n")
        self.assertEqual(
            summarize_cash_flow(self.path)["warnings"],
            ["Net cash flow for 2026-10 does not equal cash in minus cash out."],
        )

    def test_consistent_net_has_no_warning(self):
        self.path.write_text(HEADER + "2026-10,30,10,20,120\n")
        self.assertEqual(summarize_cash_flow(self.path)["warnings"], [])

    def test_negative_net_is_valid(self):
        self.path.write_text(HEADER + "2026-10,10,30,-20,80\n")
        summary = summarize_cash_flow(self.path)
        self.assertEqual(summary["net_cash_flow"], -20)
        self.assertEqual(summary["warnings"], [])


if __name__ == "__main__":
    unittest.main()
