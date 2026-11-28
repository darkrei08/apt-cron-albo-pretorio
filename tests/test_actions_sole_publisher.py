import unittest
from pathlib import Path


class ActionsSolePublisherTest(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[1]

    def read(self, relative):
        return (self.ROOT / relative).read_text(encoding="utf-8")

    def test_workflow_is_the_only_scheduled_publisher(self):
        workflow = self.read(".github/workflows/update-index.yml")
        self.assertIn("cron: '0 * * * *'", workflow)
        self.assertIn("cancel-in-progress: false", workflow)
        self.assertIn("Seed publication state from committed index", workflow)
        self.assertIn("publication_state.py", workflow)
        self.assertIn("APT_STATE_PATH: /tmp/apt-cron-state/notices.json", workflow)
        self.assertIn(
            "git add -A -- reports public/index.json public/index.md public/index.html",
            workflow,
        )
        self.assertNotIn("publication-state.json", workflow)

    def test_no_runtime_state_is_committed(self):
        self.assertFalse((self.ROOT / "publication-state.json").exists())
        adr = self.read("docs/adr/0015-actions-sole-publisher.md")
        self.assertIn("Runtime state is never committed", adr)

    def test_docs_do_not_claim_host_cron_is_active(self):
        for relative in ("README.md", "docs/operations/operator-handoff.md", "docs/ci-cd.md"):
            text = self.read(relative).lower()
            self.assertNotIn("the cron job points", text)
            self.assertNotIn("the host cron keeps", text)
            self.assertNotIn("activate the hourly cron entry", text)

    def test_adr_records_the_sole_publisher_decision(self):
        adr = self.read("docs/adr/0015-actions-sole-publisher.md")
        for needle in (
            "GitHub Actions is the only scheduler and the only publisher",
            "ephemeral state",
            "Runtime state is never committed",
            "No host-local publication job may",
        ):
            self.assertIn(needle, adr)


if __name__ == "__main__":
    unittest.main()
