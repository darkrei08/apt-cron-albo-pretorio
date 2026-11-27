import json
import tempfile
import unittest
from pathlib import Path

import apt_cron
import publication_state


class PublicationStateTest(unittest.TestCase):
    def test_state_from_index_marks_index_rows_as_already_sent(self):
        index = {
            "notices": [
                {
                    "id": 1,
                    "title": "Atto uno",
                    "detail_url": "https://example.test/dettaglio/1",
                    "document_url": "https://example.test/doc.pdf",
                    "attachment_urls": ["https://example.test/allegato.pdf"],
                }
            ]
        }

        state = publication_state.state_from_index(index)
        row = index["notices"][0]
        key = apt_cron.notice_key(row)

        self.assertEqual(state["notices"][key], apt_cron.fingerprint(row))
        self.assertEqual(state["sent_messages"][key], apt_cron.fingerprint(row))
        self.assertEqual(state["sent_documents"]["https://example.test/doc.pdf"], key)
        self.assertEqual(state["sent_documents"]["https://example.test/allegato.pdf"], key)
        self.assertEqual(state["attachments"][key]["document_url"], "https://example.test/doc.pdf")

    def test_state_from_index_ignores_unsafe_links(self):
        index = {
            "notices": [
                {
                    "id": 2,
                    "detail_url": "file:///tmp/x",
                    "document_url": "file:///tmp/x.pdf",
                    "attachment_urls": ["javascript:alert(1)"],
                }
            ]
        }

        state = publication_state.state_from_index(index)
        key = apt_cron.notice_key(index["notices"][0])

        self.assertIsNone(state["attachments"][key]["document_url"])
        self.assertEqual(state["attachments"][key]["attachment_urls"], [])
        self.assertEqual(state["sent_documents"], {})

    def test_main_writes_state_file(self):
        index = {"notices": [{"id": 3, "detail_url": "https://example.test/dettaglio/3"}]}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index_path = root / "index.json"
            state_path = root / "state.json"
            index_path.write_text(json.dumps(index), encoding="utf-8")

            self.assertEqual(
                publication_state.main(["--index", str(index_path), "--state", str(state_path)]),
                0,
            )
            state = json.loads(state_path.read_text(encoding="utf-8"))

        self.assertEqual(state["version"], 2)


if __name__ == "__main__":
    unittest.main()
