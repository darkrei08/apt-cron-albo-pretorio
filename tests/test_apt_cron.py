import json
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import apt_cron


FIXTURE = Path(__file__).parent / "fixtures" / "source_response.json"
ATTACHMENT_FIXTURE = Path(__file__).parent / "fixtures" / "attachments_response.json"

# The 41 source keys a filter response and an id query both expose, minus the 12 internal ones.
INCLUDED_SOURCE_FIELDS = (
    "id",
    "otypeId",
    "rootId",
    "rootOtypeid",
    "status",
    "cntAnnoNumeroPap",
    "cntAnnoNumeroRpap",
    "cntAutoritaMittente",
    "cntDataAnnullamento",
    "cntDataAnnullamentoTime",
    "cntDataDocumentoOrigine",
    "cntDataFinePubblicazione",
    "cntDataInizioPubblicazione",
    "cntDataNumeroPap",
    "cntDataNumeroPapTime",
    "cntDataNumeroRpap",
    "cntDataNumeroRpapTime",
    "cntDataRigetto",
    "cntDataRigettoTime",
    "cntDate",
    "cntDocumentoOrigine",
    "cntDurataPubblicazione",
    "cntExternalId",
    "cntExternalOggetto",
    "cntExternalSource",
    "cntExternalStatus",
    "cntNaturaAtto",
    "cntNaturaAttoLabel",
    "cntNoteAnnullamento",
    "cntNoteRigetto",
    "cntNumeri",
    "cntNumeroDocumentoOrigine",
    "cntNumeroGara",
    "cntNumeroPap",
    "cntNumeroRpap",
    "cntParentObjectId",
    "cntParentOtypeId",
    "cntProponente",
    "cntSettoreProponente",
    "cntSettoreProponenteLabel",
    "cntTitle",
)

EXCLUDED_SOURCE_FIELDS = (
    "cntAutore",
    "cntAutoreAnnullamento",
    "cntAutoreAnnullamentoLogin",
    "cntAutoreLogin",
    "cntAutoreRigetto",
    "cntAutoreRigettoLogin",
    "cntResponsabileProcedimento",
    "cntResponsabileProcedimentoLogin",
    "cntResponsabilePubblicazione",
    "cntResponsabilePubblicazioneLogin",
    "ultimaAnnotazioneModifica",
    "ultimaAnnotazioneRipubblicazione",
)


def first_notice():
    response = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return apt_cron.parse_source_response(response)[0]


def full_source_item():
    item = {name: f"valore {name}" for name in INCLUDED_SOURCE_FIELDS}
    for name in EXCLUDED_SOURCE_FIELDS:
        item[name] = f"PRIVATE {name}"
    item.update(
        {
            "id": 791962,
            "cntAnnoNumeroPap": 2026,
            "cntNumeroPap": 244,
            "cntDataInizioPubblicazione": "2026-11-25",
            "cntDataFinePubblicazione": "2026-12-10",
            "cntNaturaAttoLabel": "Delibera del Direttore Generale",
            "cntSettoreProponenteLabel": "UFFICIO AMMINISTRAZIONE",
            "cntTitle": "Affidamento diretto per la sala espositiva",
            "status": "PUBBLICATO",
        }
    )
    return item


def full_notice():
    return apt_cron.parse_source_response({"results": [full_source_item()]})[0]


class ParseSourceResponseTest(unittest.TestCase):
    def test_projects_every_documented_public_source_field(self):
        self.assertEqual(sorted(apt_cron.NOTICE_FIELDS.values()), sorted(INCLUDED_SOURCE_FIELDS))

        notices = apt_cron.parse_source_response({"results": [full_source_item()]})

        self.assertEqual(set(notices[0]), set(apt_cron.NOTICE_FIELDS))
        for name in EXCLUDED_SOURCE_FIELDS:
            self.assertNotIn(name, notices[0])
        self.assertNotIn("PRIVATE", json.dumps(notices))

    def test_extracts_the_fixture_values_and_drops_the_injected_person_field(self):
        response = json.loads(FIXTURE.read_text(encoding="utf-8"))

        notices = apt_cron.parse_source_response(response)

        self.assertEqual(notices[0]["id"], 791962)
        self.assertEqual(notices[0]["title"], "Affidamento diretto per la sala espositiva")
        self.assertEqual(notices[0]["category"], "Delibera del Direttore Generale")
        self.assertEqual(notices[0]["sector"], "UFFICIO AMMINISTRAZIONE")
        self.assertEqual(notices[0]["published"], "2026-11-25")
        self.assertEqual(notices[0]["expires"], "2026-12-10")
        self.assertEqual(notices[0]["year"], 2026)
        self.assertEqual(notices[0]["number"], 244)
        self.assertEqual(notices[0]["status"], "PUBBLICATO")
        self.assertIsNone(notices[0]["cntNumeroGara"])
        self.assertEqual(notices[1]["number"], 243)
        self.assertEqual(set(notices[1]), set(apt_cron.NOTICE_FIELDS))
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
                    "Scade il: 2026-12-10",
                ]
            ),
        )

    def test_includes_every_public_field_and_never_an_internal_one(self):
        notice = full_notice()
        notice.update(
            detail_url="https://example.test/albo-pretorio/dettaglio/791962",
            document_url="https://example.test/documento.pdf",
            attachment_urls=["https://example.test/allegato.pdf"],
        )

        message = apt_cron.format_message(
            notice, "https://example.test/albo-pretorio/dettaglio"
        )

        self.assertIn("Titolo: Affidamento diretto per la sala espositiva", message)
        self.assertIn("Settore: #UFFICIO_AMMINISTRAZIONE", message)
        for name in apt_cron.NOTICE_FIELDS:
            if name in apt_cron.MESSAGE_IDENTITY_FIELDS:
                continue
            self.assertIn(f"{apt_cron.FIELD_LABELS[name]}: {notice[name]}", message)
        self.assertIn("https://example.test/documento.pdf", message)
        self.assertIn("https://example.test/allegato.pdf", message)
        for name in EXCLUDED_SOURCE_FIELDS:
            self.assertNotIn(name, message)
        self.assertNotIn("PRIVATE", message)
        self.assertLessEqual(len(message), apt_cron.TELEGRAM_TEXT_LIMIT)


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
        self.assertEqual(state["version"], 2)
        self.assertEqual(set(state["notices"]), {"791962", "791960"})
        self.assertEqual(state["attachments"], {})
        self.assertEqual(state["sent_documents"], {})
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
    def __init__(self, source_response, telegram_response, attachments_response=None):
        self.source_response = source_response
        self.telegram_response = telegram_response
        self.attachments_response = attachments_response or json.loads(
            ATTACHMENT_FIXTURE.read_text(encoding="utf-8")
        )
        self.calls = []

    def request(self, method, url, payload=None):
        self.calls.append({"method": method, "url": url, "payload": payload})
        if "api.telegram.org" in url:
            return self.telegram_response
        if "/api/pap/files/" in url:
            return self.attachments_response
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
        "attachments_base": "https://example.test/api/pap/files",
        "document_base": "https://api.telegram.org/botTEST_TOKEN/sendDocument",
        "index_dir": str(Path(state_path).parent / "public"),
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
        self.assertEqual(len(transport.calls), 3)
        self.assertEqual(set(state["notices"]), {"791962", "791960"})
        self.assertEqual(set(state["attachments"]), {"791962", "791960"})

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
        self.assertEqual(len(telegram_calls), 3)
        self.assertIn("Atto aggiornato APT Basilicata", telegram_calls[0]["payload"]["text"])
        self.assertIn("Titolo aggiornato", telegram_calls[0]["payload"]["text"])
        self.assertIn("sendDocument", telegram_calls[1]["url"])
        self.assertIn("sendDocument", telegram_calls[2]["url"])
        self.assertEqual(telegram_calls[1]["payload"]["caption"], "PDF ufficiale: Atto 244/2026")

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
        self.assertNotEqual(state["notices"]["791962"], initial_state["notices"]["791962"])
        self.assertEqual(state["notices"]["791960"], old_fingerprint)


class DocumentCaptionTest(unittest.TestCase):
    def test_document_caption_uses_the_act_number_and_stays_within_telegram_limit(self):
        response = json.loads(FIXTURE.read_text(encoding="utf-8"))
        transport = SequenceTransport(response, {"ok": True, "result": {"message_id": 1}})
        with tempfile.TemporaryDirectory() as directory:
            config = run_config(Path(directory) / "state.json")
            apt_cron.run_once(transport, config)
            response["results"][0]["cntTitle"] = "A" * 5000
            transport.calls.clear()

            apt_cron.run_once(transport, config)

            documents = [
                call
                for call in transport.calls
                if "sendDocument" in call["url"]
            ]

        self.assertEqual(len(documents), 2)
        for call in documents:
            caption = call["payload"]["caption"]
            self.assertEqual(caption, "PDF ufficiale: Atto 244/2026")
            self.assertLessEqual(len(caption), apt_cron.TELEGRAM_CAPTION_LIMIT)
            self.assertNotIn("AAAA", caption)

    def test_document_caption_carries_no_public_or_internal_text(self):
        notice = full_notice()
        notice.update(title="A" * 5000)

        caption = apt_cron.document_caption(notice)

        self.assertEqual(caption, "PDF ufficiale: Atto 244/2026")
        self.assertLessEqual(len(caption), apt_cron.TELEGRAM_CAPTION_LIMIT)
        for name in EXCLUDED_SOURCE_FIELDS:
            self.assertNotIn(name, caption)
        self.assertNotIn("PRIVATE", caption)


class StableIdentityTest(unittest.TestCase):
    def test_migrates_legacy_state_without_losing_fingerprints(self):
        legacy = {"version": 1, "notices": {"791962": "old-fingerprint"}}

        migrated = apt_cron.migrate_state(legacy)

        self.assertEqual(migrated["version"], 2)
        self.assertEqual(migrated["notices"], {"791962": "old-fingerprint"})
        self.assertEqual(migrated["attachments"], {})
        self.assertEqual(migrated["sent_documents"], {})

    def test_falls_back_to_detail_url_when_id_is_missing(self):
        notice = {"detail_url": "https://example.test/albo-pretorio/dettaglio/999", "title": "x"}

        key = apt_cron.notice_key(notice)

        self.assertNotEqual(key, "None")
        self.assertEqual(key, apt_cron.notice_key(dict(notice, title="changed")))
        self.assertNotEqual(key, apt_cron.notice_key(dict(notice, detail_url="https://example.test/other")))


class PdfDeliveryTest(unittest.TestCase):
    def test_fetch_attachments_exposes_only_pdf_urls(self):
        response = json.loads((Path(__file__).parent / "fixtures" / "attachments_response.json").read_text(encoding="utf-8"))
        transport = FakeTransport(response)

        links = apt_cron.fetch_attachments(
            transport,
            "https://example.test/api/pap/files",
            791962,
        )

        self.assertEqual(transport.calls[0]["method"], "GET")
        self.assertEqual(transport.calls[0]["url"], "https://example.test/api/pap/files/791962")
        self.assertEqual(
            links,
            {
                "document_url": "https://example.test/katti/public/pap/edoc/download/unico/6500/791962",
                "attachment_urls": [
                    "https://example.test/katti/public/pap/edoc/download/single/6500/791962/abc/notice.pdf"
                ],
            },
        )

    def test_sends_pdf_by_url_as_telegram_document(self):
        transport = FakeTransport({"ok": True, "result": {"message_id": 9}})

        result = apt_cron.publish_document(
            transport,
            "https://api.telegram.org/botTEST_TOKEN/sendDocument",
            "@test_channel",
            "https://example.test/Delibera.pdf",
            "PDF ufficiale",
        )

        self.assertEqual(result["message_id"], 9)
        self.assertEqual(transport.calls[0]["method"], "POST")
        self.assertEqual(
            transport.calls[0]["payload"],
            {
                "chat_id": "@test_channel",
                "document": "https://example.test/Delibera.pdf",
                "caption": "PDF ufficiale",
            },
        )

    def test_rejects_a_document_error(self):
        transport = FakeTransport({"ok": False, "description": "file too large"})

        with self.assertRaises(RuntimeError):
            apt_cron.publish_document(transport, "https://api.telegram.org/botTEST_TOKEN/sendDocument", "@x", "https://x/a.pdf", "c")


class PublishedFieldSetTest(unittest.TestCase):
    def test_published_fields_are_the_notice_fields_plus_derived_links(self):
        self.assertEqual(
            tuple(apt_cron.INDEX_FIELDS),
            tuple(apt_cron.NOTICE_FIELDS)
            + ("detail_url", "document_url", "attachment_urls"),
        )
        for name in apt_cron.NOTICE_FIELDS:
            self.assertIn(name, apt_cron.FIELD_LABELS)
        for name in EXCLUDED_SOURCE_FIELDS:
            self.assertNotIn(name, apt_cron.NOTICE_FIELDS.values())


class PublicIndexTest(unittest.TestCase):
    def test_build_index_publishes_every_public_field(self):
        notice = full_notice()
        notice.update(
            detail_url="https://example.test/dettaglio/791962",
            document_url="https://example.test/documento.pdf",
            attachment_urls=["https://example.test/allegato.pdf"],
            responsabile="NOT PUBLIC",
        )

        index = apt_cron.build_index([notice])

        row = index["notices"][0]
        self.assertEqual(set(row), set(apt_cron.INDEX_FIELDS))
        self.assertEqual(row["title"], "Affidamento diretto per la sala espositiva")
        self.assertEqual(row["sector"], "UFFICIO AMMINISTRAZIONE")
        self.assertEqual(row["cntNumeroGara"], "valore cntNumeroGara")
        self.assertEqual(row["detail_url"], "https://example.test/dettaglio/791962")
        self.assertEqual(row["attachment_urls"], ["https://example.test/allegato.pdf"])
        self.assertNotIn("NOT PUBLIC", json.dumps(index))
        for name in EXCLUDED_SOURCE_FIELDS:
            self.assertNotIn(name, json.dumps(index))

    def test_write_index_creates_json_markdown_and_html(self):
        index = apt_cron.build_index(
            [
                dict(
                    first_notice(),
                    detail_url="https://example.test/dettaglio/791962",
                    document_url="https://example.test/documento.pdf",
                    attachment_urls=[],
                )
            ]
        )
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)

            apt_cron.write_index(target, index)
            files = {path.name: path.read_text(encoding="utf-8") for path in target.iterdir()}

        self.assertEqual(set(files), {"index.json", "index.md", "index.html"})
        self.assertIn("Affidamento diretto per la sala espositiva", files["index.md"])
        self.assertIn("Atto: 244/2026", files["index.md"])
        self.assertIn("Categoria: Delibera del Direttore Generale", files["index.md"])
        self.assertIn("Settore: UFFICIO AMMINISTRAZIONE", files["index.md"])
        self.assertIn("Stato: PUBBLICATO", files["index.md"])
        self.assertIn("https://example.test/dettaglio/791962", files["index.html"])
        self.assertIn("Affidamento diretto per la sala espositiva", files["index.html"])
        self.assertIn("Settore: UFFICIO AMMINISTRAZIONE", files["index.html"])
        self.assertIn("https://example.test/documento.pdf", files["index.json"])

    def test_write_index_renders_every_non_empty_public_field(self):
        notice = full_notice()
        notice.update(
            detail_url="https://example.test/dettaglio/791962",
            document_url=None,
            attachment_urls=[],
        )
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)

            apt_cron.write_index(target, apt_cron.build_index([notice]))
            markdown = (target / "index.md").read_text(encoding="utf-8")
            page = (target / "index.html").read_text(encoding="utf-8")

        self.assertIn("Numero gara: valore cntNumeroGara", markdown)
        self.assertIn("Autorita mittente: valore cntAutoritaMittente", page)
        for name in EXCLUDED_SOURCE_FIELDS:
            self.assertNotIn(name, markdown)
            self.assertNotIn(name, page)
        self.assertNotIn("PRIVATE", markdown)
        self.assertNotIn("PRIVATE", page)


class RefreshIndexTest(unittest.TestCase):
    def test_writes_public_index_without_state_or_telegram(self):
        response = json.loads(FIXTURE.read_text(encoding="utf-8"))
        transport = SequenceTransport(response, {"ok": True, "result": {"message_id": 1}})
        with tempfile.TemporaryDirectory() as directory:
            config = run_config(Path(directory) / "state.json")

            stats = apt_cron.refresh_index(transport, config)

            index_dir = Path(config["index_dir"])
            files = sorted(path.name for path in index_dir.iterdir())
            index = json.loads((index_dir / "index.json").read_text(encoding="utf-8"))
            state_exists = Path(config["state_path"]).exists()

        self.assertEqual(stats, {"notices": 2})
        self.assertEqual(files, ["index.html", "index.json", "index.md"])
        self.assertFalse(state_exists)
        self.assertFalse([call for call in transport.calls if "api.telegram.org" in call["url"]])
        first = index["notices"][0]
        self.assertEqual(
            first["detail_url"],
            "https://example.test/albo-pretorio/dettaglio/791962",
        )
        self.assertEqual(
            first["document_url"],
            "https://example.test/katti/public/pap/edoc/download/unico/6500/791962",
        )
        self.assertEqual(
            first["attachment_urls"],
            [
                "https://example.test/katti/public/pap/edoc/download/single/6500/791962/abc/notice.pdf"
            ],
        )
        self.assertEqual(set(first), set(apt_cron.INDEX_FIELDS))
        self.assertEqual(first["title"], "Affidamento diretto per la sala espositiva")
        self.assertEqual(first["sector"], "UFFICIO AMMINISTRAZIONE")
        self.assertNotIn("NOT IN OUTPUT", json.dumps(index))

    def test_cli_refresh_index_needs_no_telegram_credentials(self):
        response = json.loads(FIXTURE.read_text(encoding="utf-8"))
        transport = SequenceTransport(response, {"ok": True, "result": {"message_id": 1}})
        with tempfile.TemporaryDirectory() as directory:
            config = run_config(Path(directory) / "state.json")
            argv = [
                "--refresh-index",
                "--state-path",
                config["state_path"],
                "--index-dir",
                config["index_dir"],
                "--source-url",
                config["source_url"],
                "--attachments-base",
                config["attachments_base"],
            ]
            with mock.patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "", "TELEGRAM_CHAT_ID": ""}), mock.patch.object(
                apt_cron, "UrllibTransport", lambda: transport
            ), mock.patch("sys.stdout", new_callable=io.StringIO):
                code = apt_cron.main(argv)

            index_exists = (Path(config["index_dir"]) / "index.json").exists()
            state_exists = Path(config["state_path"]).exists()

        self.assertEqual(code, 0)
        self.assertTrue(index_exists)
        self.assertFalse(state_exists)
        self.assertFalse([call for call in transport.calls if "api.telegram.org" in call["url"]])


class DynamicAttachmentsTransport(SequenceTransport):
    def request(self, method, url, payload=None):
        if "/api/pap/files/" in url:
            notice_id = url.rsplit("/", 1)[1]
            response = json.loads(json.dumps(self.attachments_response))
            root = response["results"][0]
            root["documentoUnico"]["downloadUrl"] = (
                f"https://example.test/documento-{notice_id}.pdf"
            )
            for item in root["files"]:
                item["downloadUrl"] = f"https://example.test/allegato-{notice_id}.pdf"
            return response
        return super().request(method, url, payload)


class NewNoticeDeliveryTest(unittest.TestCase):
    def test_new_notice_is_published_once_then_ignored(self):
        response = json.loads(FIXTURE.read_text(encoding="utf-8"))
        transport = DynamicAttachmentsTransport(response, {"ok": True, "result": {"message_id": 1}})
        with tempfile.TemporaryDirectory() as directory:
            config = run_config(Path(directory) / "state.json")
            apt_cron.run_once(transport, config)
            response["results"].append(
                {
                    "id": 799999,
                    "cntTitle": "Nuovo affidamento",
                    "cntAnnoNumeroPap": 2026,
                    "cntNumeroPap": 250,
                    "cntDataInizioPubblicazione": "2026-11-25",
                    "cntDataFinePubblicazione": "2026-12-10",
                    "cntNaturaAttoLabel": "Delibera",
                    "cntSettoreProponenteLabel": "UFFICIO",
                    "status": "PUBBLICATO",
                }
            )
            transport.calls.clear()

            stats = apt_cron.run_once(transport, config)
            first_calls = list(transport.calls)
            state = apt_cron.load_state(config["state_path"])
            transport.calls.clear()

            second_stats = apt_cron.run_once(transport, config)

        self.assertEqual(stats["published"], 1)
        self.assertEqual(second_stats["published"], 0)
        sent = [call for call in first_calls if "api.telegram.org" in call["url"]]
        self.assertEqual(len(sent), 3)
        self.assertEqual(sent[1]["payload"]["document"], "https://example.test/documento-799999.pdf")
        self.assertEqual(sent[2]["payload"]["document"], "https://example.test/allegato-799999.pdf")
        self.assertIn("https://example.test/documento-799999.pdf", state["sent_documents"])
        self.assertIn("https://example.test/allegato-799999.pdf", state["sent_documents"])
        self.assertFalse([call for call in transport.calls if "api.telegram.org" in call["url"]])

    def test_pdf_is_not_sent_again_when_notice_changes_again(self):
        response = json.loads(FIXTURE.read_text(encoding="utf-8"))
        transport = DynamicAttachmentsTransport(response, {"ok": True, "result": {"message_id": 1}})
        with tempfile.TemporaryDirectory() as directory:
            config = run_config(Path(directory) / "state.json")
            apt_cron.run_once(transport, config)
            response["results"][0]["cntTitle"] = "Primo aggiornamento"
            transport.calls.clear()
            apt_cron.run_once(transport, config)
            response["results"][0]["cntTitle"] = "Secondo aggiornamento"
            transport.calls.clear()

            apt_cron.run_once(transport, config)

            sent = [call for call in transport.calls if "api.telegram.org" in call["url"]]

        self.assertEqual(len(sent), 1)
        self.assertIn("sendMessage", sent[0]["url"])


class ProductionConfigTest(unittest.TestCase):
    def test_page_size_must_be_a_positive_integer(self):
        self.assertEqual(apt_cron.parse_positive_int("20", "APT_PAGE_SIZE"), 20)
        for value in ("bad", "0", "-1", ""):
            with self.subTest(value=value), self.assertRaises(ValueError):
                apt_cron.parse_positive_int(value, "APT_PAGE_SIZE")

    def test_redacts_telegram_token_from_error_text(self):
        error = "HTTP 401 at https://api.telegram.org/botSUPERSECRET/sendMessage"

        redacted = apt_cron.redact_credentials(error, "SUPERSECRET")

        self.assertNotIn("SUPERSECRET", redacted)
        self.assertIn("[REDACTED]", redacted)

    def test_message_stays_within_telegram_text_limit(self):
        notice = full_notice()
        for name in apt_cron.NOTICE_FIELDS:
            if name not in ("published", "expires"):
                notice[name] = "x" * 500
        notice.update(number=244, year=2026)
        notice["detail_url"] = "https://example.test/albo-pretorio/dettaglio/" + "a" * 5000

        message = apt_cron.format_message(
            notice,
            "https://example.test/albo-pretorio/dettaglio",
        )

        self.assertLessEqual(len(message), apt_cron.TELEGRAM_TEXT_LIMIT)
        self.assertIn("Titolo:", message)


if __name__ == "__main__":
    unittest.main()
