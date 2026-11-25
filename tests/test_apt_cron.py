import json
from pathlib import Path
import tempfile
import unittest

import apt_cron


FIXTURE = Path(__file__).parent / "fixtures" / "source_response.json"


def first_notice():
    response = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return apt_cron.parse_source_response(response)[0]


class ParseSourceResponseTest(unittest.TestCase):
    def test_extracts_only_allowed_notice_fields(self):
        response = json.loads(FIXTURE.read_text(encoding="utf-8"))

        notices = apt_cron.parse_source_response(response)

        self.assertEqual(
            notices,
            [
                {
                    "id": 791962,
                    "title": "Affidamento diretto per la sala espositiva",
                    "category": "Delibera del Direttore Generale",
                    "sector": "UFFICIO AMMINISTRAZIONE",
                    "published": "2026-11-25",
                    "expires": "2026-12-10",
                    "year": 2026,
                    "number": 244,
                    "status": "PUBBLICATO",
                },
                {
                    "id": 791960,
                    "title": "D.G.R. N. 462 del 28.07.2026",
                    "category": "Delibera del Direttore Generale",
                    "sector": "UFFICIO AMMINISTRAZIONE",
                    "published": "2026-11-25",
                    "expires": "2026-12-10",
                    "year": 2026,
                    "number": 243,
                    "status": "PUBBLICATO",
                },
            ],
        )
        self.assertNotIn("NOT IN OUTPUT", json.dumps(notices))
        self.assertNotIn("ALSO NOT IN OUTPUT", json.dumps(notices))


class FormatMessageTest(unittest.TestCase):
    def test_formats_plain_text_with_searchable_fields_and_official_link(self):
        notice = first_notice()

        message = apt_cron.format_message(
            notice,
            "https://siopi.publisys.it/sito-aptbasilicata/albo-pretorio/dettaglio",
        )

        self.assertEqual(
            message,
            "\n".join(
                [
                    "Nuovo atto APT Basilicata",
                    "Data: 25/11/2026",
                    "Titolo: Affidamento diretto per la sala espositiva",
                    "Categoria: #Delibera_del_Direttore_Generale",
                    "Settore: #UFFICIO_AMMINISTRAZIONE",
                    "Atto: 244/2026",
                    "Stato: PUBBLICATO",
                    "Link: https://siopi.publisys.it/sito-aptbasilicata/albo-pretorio/dettaglio/791962",
                ]
            ),
        )


class FakeTransport:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def request(self, method, url, payload=None):
        self.calls.append({"method": method, "url": url, "payload": payload})
        return self.response


class FetchNoticesTest(unittest.TestCase):
    def test_posts_only_a_read_query_to_the_official_source(self):
        response = json.loads(FIXTURE.read_text(encoding="utf-8"))
        transport = FakeTransport(response)

        notices = apt_cron.fetch_notices(
            transport,
            "https://siopi.publisys.it/kapi-aptbasilicata/api/pap/filter",
            "2026-11-25",
            "200152",
            20,
        )

        self.assertEqual(len(notices), 2)
        self.assertEqual(transport.calls[0]["method"], "POST")
        self.assertEqual(
            transport.calls[0]["url"],
            "https://siopi.publisys.it/kapi-aptbasilicata/api/pap/filter?page=0&size=20",
        )
        self.assertEqual(
            transport.calls[0]["payload"],
            {
                "dataOption": "all",
                "papSearchCriteriaList": [
                    {"filterKey": "cntNaturaAtto", "operation": "eq", "value": "200152"},
                    {
                        "filterKey": "cntDataFinePubblicazione",
                        "operation": "ge",
                        "value": "2026-11-25",
                    },
                    {
                        "filterKey": "cntDataInizioPubblicazione",
                        "operation": "le",
                        "value": "2026-11-25",
                    },
                    {"filterKey": "cntExternalStatus", "operation": "nu", "value": ""},
                    {"filterKey": "cntNumeroPap", "operation": "nn"},
                    {"filterKey": "cntAnnoNumeroPap", "operation": "nn"},
                ],
            },
        )

    def test_rejects_an_error_response(self):
        transport = FakeTransport({"error": True, "errorMessage": "bad request", "results": []})

        with self.assertRaises(RuntimeError):
            apt_cron.fetch_notices(transport, "https://example.test/filter", "2026-11-25", "1", 20)


class PublishMessageTest(unittest.TestCase):
    def test_posts_plain_text_to_telegram(self):
        transport = FakeTransport({"ok": True, "result": {"message_id": 1}})

        result = apt_cron.publish_message(
            transport, "https://api.telegram.org/botTEST_TOKEN/sendMessage", "@test_channel", "test text"
        )

        self.assertEqual(result["message_id"], 1)
        self.assertEqual(transport.calls[0]["method"], "POST")
        self.assertEqual(
            transport.calls[0]["url"],
            "https://api.telegram.org/botTEST_TOKEN/sendMessage",
        )
        self.assertEqual(
            transport.calls[0]["payload"],
            {"chat_id": "@test_channel", "text": "test text"},
        )

    def test_rejects_a_telegram_error(self):
        transport = FakeTransport({"ok": False, "description": "chat not found"})

        with self.assertRaises(RuntimeError):
            apt_cron.publish_message(transport, "https://api.telegram.org/botTEST_TOKEN/sendMessage", "@x", "hi")


class DeduplicationTest(unittest.TestCase):
    def test_first_run_seeds_state_without_posting(self):
        notices = apt_cron.parse_source_response(json.loads(FIXTURE.read_text(encoding="utf-8")))

        changes, state = apt_cron.select_changes(notices, None)

        self.assertEqual(changes, [])
        self.assertEqual(state["version"], 1)
        self.assertEqual(set(state["notices"]), {"791962", "791960"})
        self.assertTrue(all(isinstance(value, str) for value in state["notices"].values()))

    def test_changed_notice_is_reported_once_as_update(self):
        notices = apt_cron.parse_source_response(json.loads(FIXTURE.read_text(encoding="utf-8")))
        _, state = apt_cron.select_changes(notices, None)
        changed = [dict(notices[0], title="Updated title")]

        changes, next_state = apt_cron.select_changes(changed + [notices[1]], state)

        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0][0]["id"], 791962)
        self.assertTrue(changes[0][1])
        self.assertNotEqual(next_state["notices"]["791962"], state["notices"]["791962"])

    def test_state_round_trip_in_temporary_directory(self):
        notices = apt_cron.parse_source_response(json.loads(FIXTURE.read_text(encoding="utf-8")))
        _, state = apt_cron.select_changes(notices, None)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"

            apt_cron.save_state(path, state)
            loaded = apt_cron.load_state(path)

        self.assertEqual(loaded, state)
        self.assertFalse(path.exists())


class SequenceTransport:
    def __init__(self, source_response, telegram_response):
        self.source_response = source_response
        self.telegram_response = telegram_response
        self.calls = []

    def request(self, method, url, payload=None):
        self.calls.append({"method": method, "url": url, "payload": payload})
        if "api.telegram.org" in url:
            return self.telegram_response
        return self.source_response


def run_config(state_path):
    return {
        "source_url": "https://example.test/filter",
        "today": "2026-11-25",
        "nature_id": "200152",
        "size": 20,
        "telegram_url": "https://api.telegram.org/botTEST_TOKEN/sendMessage",
        "chat_id": "@test_channel",
        "detail_base": "https://example.test/albo-pretorio/dettaglio",
        "state_path": str(state_path),
    }


class RunOnceTest(unittest.TestCase):
    def test_first_run_seeds_state_and_does_not_publish(self):
        response = json.loads(FIXTURE.read_text(encoding="utf-8"))
        transport = SequenceTransport(response, {"ok": True, "result": {"message_id": 1}})
        with tempfile.TemporaryDirectory() as directory:
            config = run_config(Path(directory) / "state.json")

            stats = apt_cron.run_once(transport, config)
            state = apt_cron.load_state(config["state_path"])

        self.assertEqual(stats, {"notices": 2, "published": 0, "dry_run": False})
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(set(state["notices"]), {"791962", "791960"})

    def test_changed_notice_is_published_once_with_update_label(self):
        response = json.loads(FIXTURE.read_text(encoding="utf-8"))
        transport = SequenceTransport(response, {"ok": True, "result": {"message_id": 2}})
        with tempfile.TemporaryDirectory() as directory:
            config = run_config(Path(directory) / "state.json")
            apt_cron.run_once(transport, config)
            response["results"][0]["cntTitle"] = "Titolo aggiornato"
            transport.calls.clear()

            stats = apt_cron.run_once(transport, config)

        self.assertEqual(stats["published"], 1)
        telegram_calls = [call for call in transport.calls if "api.telegram.org" in call["url"]]
        self.assertEqual(len(telegram_calls), 1)
        self.assertIn("Atto aggiornato APT Basilicata", telegram_calls[0]["payload"]["text"])
        self.assertIn("Titolo aggiornato", telegram_calls[0]["payload"]["text"])

    def test_dry_run_does_not_publish_or_write_state(self):
        response = json.loads(FIXTURE.read_text(encoding="utf-8"))
        response["results"][0]["cntTitle"] = "Titolo aggiornato"
        transport = SequenceTransport(response, {"ok": True, "result": {"message_id": 3}})
        with tempfile.TemporaryDirectory() as directory:
            config = run_config(Path(directory) / "state.json")
            response["results"][0]["cntTitle"] = "Titolo originale"
            apt_cron.run_once(transport, config)
            transport.calls.clear()
            config["dry_run"] = True
            response["results"][0]["cntTitle"] = "Titolo aggiornato"

            stats = apt_cron.run_once(transport, config)

            self.assertEqual(stats, {"notices": 2, "published": 1, "dry_run": True})
            self.assertEqual(len(transport.calls), 1)
            self.assertTrue(apt_cron.load_state(config["state_path"]))


class FailingSecondTransport(SequenceTransport):
    def __init__(self, source_response):
        super().__init__(source_response, {"ok": True, "result": {"message_id": 1}})
        self.telegram_calls = 0

    def request(self, method, url, payload=None):
        if "api.telegram.org" in url:
            self.telegram_calls += 1
            if self.telegram_calls == 2:
                return {"ok": False, "description": "chat not found"}
        return super().request(method, url, payload)


class PartialFailureTest(unittest.TestCase):
    def test_successful_publish_is_not_repeated_after_a_later_failure(self):
        response = json.loads(FIXTURE.read_text(encoding="utf-8"))
        transport = FailingSecondTransport(response)
        with tempfile.TemporaryDirectory() as directory:
            config = run_config(Path(directory) / "state.json")
            apt_cron.run_once(transport, config)
            initial_state = apt_cron.load_state(config["state_path"])
            old_fingerprint = initial_state["notices"]["791960"]
            for item in response["results"]:
                item["cntTitle"] += " aggiornato"
            transport.calls.clear()

            with self.assertRaises(RuntimeError):
                apt_cron.run_once(transport, config)
            state = apt_cron.load_state(config["state_path"])

        self.assertEqual(transport.telegram_calls, 2)
        expected = apt_cron.fingerprint(apt_cron.parse_source_response(response)[0])
        self.assertEqual(state["notices"]["791962"], expected)
        self.assertEqual(state["notices"]["791960"], old_fingerprint)


if __name__ == "__main__":
    unittest.main()
