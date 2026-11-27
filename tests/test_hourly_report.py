import json
import tempfile
import unittest
from pathlib import Path

import hourly_report


def notice(notice_id, title="Atto", document_url=None):
    return {
        "id": notice_id,
        "title": title,
        "detail_url": f"https://example.test/dettaglio/{notice_id}",
        "document_url": document_url,
        "attachment_urls": [],
    }


class ReportTest(unittest.TestCase):
    def test_detects_new_changed_and_removed_notices(self):
        before = [notice(1, "Atto uno"), notice(2, "Atto due")]
        after = [notice(1, "Atto uno"), notice(2, "Atto due modificato"), notice(3, "Atto tre")]

        report = hourly_report.build_report(
            before, after, timestamp="2026-11-27T18:00:00+01:00"
        )

        self.assertEqual(report["counts"], {
            "after": 3,
            "before": 2,
            "changed": 1,
            "new": 1,
            "removed": 0,
            "unchanged": 1,
        })
        self.assertEqual(report["outcome"], "new_acts")
        self.assertEqual(report["ids"]["new"], ["3"])
        self.assertEqual(report["ids"]["changed"], ["2"])
        self.assertEqual(report["timestamp"], "2026-11-27T18:00:00+01:00")

    def test_reports_no_changes_after_rerun(self):
        rows = [notice(1, "Atto uno"), notice(2, "Atto due")]

        report = hourly_report.build_report(
            rows, rows, timestamp="2026-11-27T18:00:00+01:00"
        )

        self.assertEqual(report["outcome"], "no_changes")
        self.assertEqual(report["counts"]["new"], 0)
        self.assertEqual(report["counts"]["changed"], 0)
        self.assertEqual(report["counts"]["removed"], 0)
        self.assertEqual(report["counts"]["unchanged"], 2)
        self.assertIn("no changes", report["message"])

    def test_reports_changed_without_new_acts(self):
        before = [notice(1, "Atto uno")]
        after = [notice(1, "Atto uno modificato")]

        report = hourly_report.build_report(before, after)

        self.assertEqual(report["outcome"], "changed_acts")
        self.assertIn("No new acts", report["message"])
        self.assertIn("Changed acts: 1", report["message"])

    def test_stats_report_reads_dry_run_counts(self):
        report = hourly_report.build_stats_report(
            {"notices": 23, "published": 0, "dry_run": True}
        )

        self.assertEqual(report["outcome"], "no_new_acts_to_publish")
        self.assertEqual(report["counts"], {"notices": 23, "published": 0, "errors": 0, "dry_run": True})
        self.assertIn("No new or changed acts to publish", report["message"])

    def test_run_report_distinguishes_outcomes(self):
        seeded = hourly_report.build_run_report({"notices": 23, "seeded": True})
        new = hourly_report.build_run_report({"notices": 23, "new": 2})
        changed = hourly_report.build_run_report({"notices": 23, "changed": 1})
        none = hourly_report.build_run_report({"notices": 23})

        self.assertEqual(seeded["outcome"], "seeded")
        self.assertEqual(new["outcome"], "new_acts")
        self.assertEqual(changed["outcome"], "changed_acts")
        self.assertEqual(none["outcome"], "no_changes")
        self.assertIn("no changes", none["message"])

    def test_combined_markdown_contains_index_and_publication_results(self):
        index_report = hourly_report.build_report(
            [notice(1)], [notice(1), notice(2)], timestamp="2026-11-27T18:00:00+01:00"
        )
        stats_report = hourly_report.build_stats_report(
            {"notices": 2, "published": 1, "dry_run": False},
            timestamp="2026-11-27T18:00:00+01:00",
        )

        text = hourly_report.combined_markdown(index_report, stats_report)

        self.assertIn("# Hourly publication report", text)
        self.assertIn("Acts to publish: 1", text)
        self.assertIn("New acts to download: 1", text)
        self.assertIn("| New acts in index | 1 |", text)

    def test_write_report_creates_json_and_markdown(self):
        report = hourly_report.build_report(
            [notice(1)], [notice(1)], timestamp="2026-11-27T18:00:00+01:00"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            json_path = root / "report.json"
            markdown_path = root / "report.md"
            hourly_report.write_report(report, json_path, markdown_path)

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            markdown = markdown_path.read_text(encoding="utf-8")

        self.assertEqual(payload, report)
        self.assertIn("2026-11-27T18:00:00+01:00", markdown)
        self.assertIn("New acts: 0", markdown)
        self.assertIn("No new acts to download and no changes.", markdown)


if __name__ == "__main__":
    unittest.main()
