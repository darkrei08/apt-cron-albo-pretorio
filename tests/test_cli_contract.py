import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock
from pathlib import Path

import apt_cron
import daily_report
import hourly_report
import publication_state


class CliContractTest(unittest.TestCase):
    def test_registry_describes_the_current_entrypoints(self):
        root = Path(__file__).resolve().parents[1]
        registry = json.loads((root / "docs/validation/cli-contract.json").read_text(encoding="utf-8"))

        self.assertEqual(registry["name"], "cron-albo-pretorio")
        self.assertEqual(registry["runtime"], "python3-stdlib")
        self.assertEqual(registry["runtime_tools"], [])
        self.assertEqual(registry["exit_codes"]["2"], "invalid arguments, unknown Telegram profile or invalid APT_PAGE_SIZE")
        self.assertEqual(
            registry["optional_count_fields"], ["attachment_errors", "document_errors"]
        )
        for entry in registry["entry_points"]:
            self.assertTrue((root / entry["module"]).is_file())
            self.assertIn(entry["stdout"], {"json", "markdown", "none"})
            self.assertEqual(registry["contract"], "docs/cli-contract.md")
        dry_run = next(item for item in registry["entry_points"] if item["id"] == "apt_cron_dry_run")
        self.assertEqual(dry_run["command"], ["python3", "apt_cron.py", "--dry-run"])
        self.assertEqual(dry_run["required_success_keys"], ["notices", "published", "dry_run"])

    def test_dry_run_prints_one_json_object(self):
        stats = {"notices": 20, "published": 0, "dry_run": True}
        with tempfile.TemporaryDirectory() as directory:
            env = {
                "APT_ENV_FILE": str(Path(directory) / "missing.env"),
                "APT_PAGE_SIZE": "20",
                "APT_STATE_PATH": str(Path(directory) / "state.json"),
            }
            stdout = io.StringIO()
            with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(
                apt_cron, "UrllibTransport", lambda: object()
            ), mock.patch.object(apt_cron, "run_once", lambda transport, config: stats), redirect_stdout(
                stdout
            ):
                code = apt_cron.main(["--dry-run"])

        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), stats)
        self.assertEqual(len(stdout.getvalue().splitlines()), 1)

    def test_runtime_error_returns_one_and_redacts_token(self):
        token = "SECRET_TOKEN"
        env = {
            "APT_ENV_FILE": "/nonexistent",
            "APT_TELEGRAM_PROFILE": "test",
            "APT_TEST_TELEGRAM_BOT_TOKEN": token,
            "APT_TEST_TELEGRAM_CHAT_ID": "@test",
            "APT_PAGE_SIZE": "20",
        }

        def fail(transport, config):
            raise RuntimeError(f"telegram error {token}")

        stderr = io.StringIO()
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(
            apt_cron, "UrllibTransport", lambda: object()
        ), mock.patch.object(apt_cron, "run_once", fail), redirect_stderr(stderr):
            code = apt_cron.main(["--backfill"])

        self.assertEqual(code, 1)
        self.assertTrue(stderr.getvalue().startswith("error:"))
        self.assertNotIn(token, stderr.getvalue())

    def test_invalid_profile_returns_two(self):
        env = {
            "APT_ENV_FILE": "/nonexistent",
            "APT_TELEGRAM_PROFILE": "staging",
            "APT_PAGE_SIZE": "20",
        }
        stderr = io.StringIO()
        with mock.patch.dict(os.environ, env, clear=True), redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as caught:
                apt_cron.main(["--dry-run"])

        self.assertEqual(caught.exception.code, 2)

    def test_report_builders_exit_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index = root / "index.json"
            stats = root / "stats.json"
            index.write_text('{"notices": []}', encoding="utf-8")
            stats.write_text('{"notices": 0, "published": 0, "dry_run": true}', encoding="utf-8")
            hourly_out = io.StringIO()
            with redirect_stdout(hourly_out):
                hourly_code = hourly_report.main(["--stats", str(stats), "--stdout"])
            daily_out = root / "daily.md"
            daily_code = daily_report.main(
                ["--date", "2026-11-27", "--input-dir", str(root), "--output", str(daily_out)]
            )
            state_out = root / "state.json"

            state_code = publication_state.main(
                ["--index", str(index), "--state", str(state_out)]
            )
            daily_exists = daily_out.exists()
            state_exists = state_out.exists()

        self.assertEqual(hourly_code, 0)
        self.assertEqual(daily_code, 0)
        self.assertEqual(state_code, 0)
        self.assertIn("# Hourly publication check", hourly_out.getvalue())
        self.assertTrue(daily_exists)
        self.assertTrue(state_exists)


if __name__ == "__main__":
    unittest.main()
