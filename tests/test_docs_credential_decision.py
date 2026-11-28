import re
import unittest
from pathlib import Path


class CredentialDecisionDocsTest(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[1]
    DOCS = [
        "README.md",
        "GLOSSARY.md",
        "docs/ci-cd.md",
        "docs/adr/0003-production-secret-storage-and-schedule.md",
        "docs/adr/0006-notification-format-and-channel.md",
        "docs/adr/0007-release-gate.md",
        "docs/adr/0014-production-credential-override-and-destination-channel.md",
        "docs/operations/production-runbook.md",
        "docs/operations/operator-handoff.md",
        "docs/validation/telegram-private-channel.md",
    ]

    def read(self, relative):
        return (self.ROOT / relative).read_text(encoding="utf-8")

    def test_adr_records_the_operator_override(self):
        text = self.read(
            "docs/adr/0014-production-credential-override-and-destination-channel.md"
        )
        for needle in (
            "APT_TEST_TELEGRAM_CHAT_ID",
            "host cron keeps `APT_TELEGRAM_PROFILE=production`",
            "must be rotated before GO",
            "Destination channel for Public notices",
        ):
            self.assertIn(needle, text)

    def test_no_active_private_validation_instruction(self):
        checklist = self.read("docs/validation/telegram-private-channel.md")
        self.assertNotIn("rerun V4 in the private validation channel", checklist)
        self.assertIn("Destination channel under ADR 0014", checklist)

        readme = self.read("README.md")
        self.assertNotIn("never reused as production credentials", readme)
        ci_cd = self.read("docs/ci-cd.md")
        self.assertNotIn("protected test Telegram repository secrets", ci_cd)

    def test_relative_links_in_changed_docs_resolve(self):
        for relative in self.DOCS:
            source = self.ROOT / relative
            for link in re.findall(r"\[[^\]]+\]\(([^)]+)\)", source.read_text(encoding="utf-8")):
                if re.match(r"^[a-z]+://", link) or link.startswith("#"):
                    continue
                target = link.split("#")[0]
                if target:
                    self.assertTrue(
                        (source.parent / target).resolve().exists(),
                        f"broken link in {relative}: {link}",
                    )


if __name__ == "__main__":
    unittest.main()
