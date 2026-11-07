"""Checks for the GitHub Actions schedule."""

import re
import unittest
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

WORKFLOW = Path(__file__).parent / ".github" / "workflows" / "daily_report.yml"


class TestSchedule(unittest.TestCase):
    def setUp(self):
        self.text = WORKFLOW.read_text(encoding="utf-8")

    def test_runs_at_0730_wib_every_weekday_and_never_on_weekends(self):
        minute, hour, day, month, weekdays = re.findall(r"cron:\s*'([^']+)'", self.text)[0].split()
        self.assertEqual((day, month, weekdays), ("*", "*", "1-5"))
        # November 9, 2026 is a Monday. Cron counts Monday as 1 and Friday as 5.
        for offset in range(5):
            utc_run = datetime(2026, 11, 9 + offset, int(hour), int(minute), tzinfo=timezone.utc)
            wib_run = utc_run.astimezone(ZoneInfo("Asia/Jakarta"))
            self.assertEqual(wib_run.strftime("%H:%M"), "07:30")
            self.assertEqual(wib_run.isoweekday(), offset + 1)

    def test_only_one_schedule_is_set(self):
        self.assertEqual(len(re.findall(r"cron:", self.text)), 1)

    def test_key_comes_from_a_github_secret(self):
        self.assertIn("SECTORS_API_KEY: ${{ secrets.SECTORS_API_KEY }}", self.text)
        self.assertEqual(len(re.findall(r"SECTORS_API_KEY:", self.text)), 1)

    def test_saved_files_are_committed_even_when_the_run_fails(self):
        self.assertIn("git add -A -- reports logs data", self.text)
        self.assertIn("if: always()", self.text)

    def test_a_failed_run_still_shows_as_failed(self):
        self.assertIn("steps.report.outcome == 'failure'", self.text)
        self.assertIn("exit 1", self.text)


if __name__ == "__main__":
    unittest.main()
