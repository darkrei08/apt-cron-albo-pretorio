import unittest
from pathlib import Path


class TestPhaseTicketsTest(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[1]

    def read(self, relative):
        return (self.ROOT / relative).read_text(encoding="utf-8")

    def test_scheduling_adr_supersession_is_recorded(self):
        for relative in (
            "docs/adr/0003-production-secret-storage-and-schedule.md",
            "docs/adr/0007-release-gate.md",
        ):
            text = self.read(relative)
            self.assertIn("Superseded by [ADR 0015]", text)

    def test_monitoring_owner_and_alert_are_named(self):
        for relative in (
            "docs/operations/production-runbook.md",
            "docs/operations/operator-handoff.md",
        ):
            text = self.read(relative)
            self.assertIn("Observer: `darkrei08`", text)
            self.assertIn("Alert destination: GitHub Actions job notifications", text)
            self.assertIn("Incident trigger: a failed workflow or unexpected publication count", text)

    def test_test_phase_gate_record_is_complete(self):
        text = self.read("docs/validation/test-phase-gate.md")
        for needle in (
            "Ticket 29",
            "Ticket 31",
            "Ticket 30",
            "Ticket 32",
            "NOT RUN",
            "NO-GO",
            "token rotation",
        ):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
