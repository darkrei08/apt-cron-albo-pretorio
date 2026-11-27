import json
import tempfile
import unittest
from pathlib import Path

import apt_cron
import portal_monitor

FIXTURE = Path(__file__).parent / "fixtures" / "source_response.json"


class FakeTransport:
    def __init__(self, response=None, payloads=None, error=None, fetch_error=None):
        self.response = response
        self.payloads = payloads or {}
        self.error = error
        self.fetch_error = fetch_error
        self.calls = []

    def request(self, method, url, payload=None):
        self.calls.append({"method": method, "url": url, "payload": payload})
        if self.error is not None:
            raise self.error
        return self.response

    def fetch_bytes(self, url):
        self.calls.append({"method": "GET", "url": url, "payload": None})
        if self.fetch_error is not None:
            raise self.fetch_error
        return self.payloads.get(url, b"pdf")


def config(directory, **overrides):
    values = {
        "source_url": "https://example.test/api/pap/filter",
        "attachments_base": "https://example.test/api/pap/files",
        "detail_base": "https://example.test/albo-pretorio/dettaglio",
        "history_path": str(Path(directory) / "portal-history.json"),
        "today": "2026-11-27",
        "nature_id": "200152",
        "size": 20,
        "dry_run": False,
        "alert_token": "",
        "alert_chat_id": "",
    }
    values.update(overrides)
    return values


class SnapshotTest(unittest.TestCase):
    def test_snapshot_records_structure_notices_and_digest(self):
        response = json.loads(FIXTURE.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as directory:
            snapshot, probe_error = portal_monitor.build_snapshot(
                FakeTransport(response), config(directory)
            )

        self.assertIsNone(probe_error)
        self.assertEqual(snapshot["structure"]["response_keys"], sorted(response.keys()))
        self.assertEqual(snapshot["structure"]["results_count"], len(response["results"]))
        self.assertEqual(snapshot["structure"]["total_pages"], response["totalPages"])
        self.assertEqual(len(snapshot["notices"]), len(response["results"]))
        self.assertEqual(snapshot["notices"][0]["id"], response["results"][0]["id"])
        self.assertEqual(len(snapshot["digest"]), 64)

    def test_attachment_probe_failure_is_reported(self):
        response = json.loads(FIXTURE.read_text(encoding="utf-8"))
        response["results"][0]["documentoUnico"] = {
            "mimeType": "application/pdf",
            "downloadUrl": "https://example.test/document.pdf",
        }
        error = RuntimeError("download blocked")
        with tempfile.TemporaryDirectory() as directory:
            _, probe_error = portal_monitor.build_snapshot(
                FakeTransport(response, fetch_error=error), config(directory)
            )
        self.assertEqual(probe_error, "download blocked")


class DiffTest(unittest.TestCase):
    def test_diff_detects_added_removed_and_changed_notices(self):
        previous = {
            "structure": {"response_keys": ["results"], "notice_keys": ["id"], "total_pages": 1},
            "notices": [
                {"key": "a", "fingerprint": "1", "detail_url": "u1", "attachment_urls": []},
                {"key": "b", "fingerprint": "2", "detail_url": "u2", "attachment_urls": []},
            ],
            "digest": "old",
        }
        current = {
            "structure": {"response_keys": ["error", "results"], "notice_keys": ["id"], "total_pages": 2},
            "notices": [
                {"key": "a", "fingerprint": "1", "detail_url": "changed", "attachment_urls": []},
                {"key": "c", "fingerprint": "3", "detail_url": "u3", "attachment_urls": []},
            ],
            "digest": "new",
        }

        changes = portal_monitor.diff_snapshots(previous, current)

        self.assertIn("response keys changed: results -> error, results", changes)
        self.assertIn("total pages changed: 1 -> 2", changes)
        self.assertIn("notice a detail url changed", changes)
        self.assertIn("notice b removed", changes)
        self.assertIn("notice c added", changes)
        self.assertNotIn("notice a fingerprint changed", changes)


class HistoryTest(unittest.TestCase):
    def test_append_event_bounds_history_and_keeps_latest(self):
        history = {"version": 1, "events": []}
        for index in range(205):
            portal_monitor.append_event(history, {"number": index}, limit=200)
        self.assertEqual(len(history["events"]), 200)
        self.assertEqual(history["events"][0]["number"], 5)
        self.assertEqual(history["events"][-1]["number"], 204)

    def test_baseline_stores_snapshot_without_alerting(self):
        response = json.loads(FIXTURE.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as directory:
            transport = FakeTransport(response)
            settings = config(directory, alert_token="secret", alert_chat_id="chat")
            result = portal_monitor.run_monitor(transport, settings)
            history = json.loads(Path(settings["history_path"]).read_text(encoding="utf-8"))
            self.assertFalse(any("api.telegram.org" in call["url"] for call in transport.calls))
            self.assertIsNotNone(history["last_snapshot"])
            self.assertEqual(history["events"][0]["status"], "changed")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["alerted"], False)

    def test_dry_run_does_not_write_or_alert(self):
        response = json.loads(FIXTURE.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as directory:
            transport = FakeTransport(response)
            result = portal_monitor.run_monitor(
                transport,
                config(directory, dry_run=True, alert_token="secret", alert_chat_id="chat"),
            )
            self.assertFalse(Path(config(directory)["history_path"]).exists())
            self.assertFalse(any("api.telegram.org" in call["url"] for call in transport.calls))
        self.assertEqual(result["alerted"], False)


class AlertTest(unittest.TestCase):
    def test_alert_uses_dedicated_chat_and_redacts_token(self):
        token = "secret-token"
        transport = FakeTransport(error=RuntimeError(f"telegram rejected {token}"))
        with self.assertRaises(RuntimeError) as caught:
            portal_monitor.send_alert(transport, token, "alert-chat", "site down")
        self.assertNotIn(token, str(caught.exception))
        self.assertEqual(transport.calls[0]["payload"]["chat_id"], "alert-chat")
        self.assertEqual(transport.calls[0]["payload"]["text"], "site down")


if __name__ == "__main__":
    unittest.main()
