import tempfile
import unittest
from pathlib import Path

import daily_report


class DailyReportTest(unittest.TestCase):
    def test_aggregates_hourly_reports(self):
        first = """# Hourly publication report

- Checked at: 2026-11-27T09:00:00+01:00 (Europe/Rome)
- Outcome: new_acts
- Result: New acts to download: 2
- New acts: 2
- Changed acts: 0
- Acts no longer published: 0
"""
        second = """# Hourly publication report

- Checked at: 2026-11-27T10:00:00+01:00 (Europe/Rome)
- Outcome: no_changes
- Result: No new acts to download and no changes.
- New acts: 0
- Changed acts: 0
- Acts no longer published: 0
"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "0900.md").write_text(first, encoding="utf-8")
            (root / "1000.md").write_text(second, encoding="utf-8")
            rows = [daily_report.parse_report(root / "0900.md"), daily_report.parse_report(root / "1000.md")]
            text = daily_report.markdown("2026-11-27", rows)

        self.assertEqual(sum(row["new"] for row in rows), 2)
        self.assertIn("| Hourly reports | 2 |", text)
        self.assertIn("| New acts | 2 |", text)
        self.assertIn("0900.md", text)
        self.assertIn("new_acts", text)

    def test_empty_day_is_reported(self):
        text = daily_report.markdown("2026-11-27", [])
        self.assertIn("| Hourly reports | 0 |", text)
        self.assertIn("no_runs", text)


if __name__ == "__main__":
    unittest.main()
