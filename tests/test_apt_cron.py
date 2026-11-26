import json
import io
import os
import contextlib
import re
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


def archive_item(notice_id, published, number):
    return {
        "id": notice_id,
        "cntTitle": f"Atto archivio {number}",
        "cntAnnoNumeroPap": 2026,
        "cntNumeroPap": number,
        "cntDataInizioPubblicazione": published,
        "cntDataFinePubblicazione": "2026-12-31",
        "cntNaturaAttoLabel": "Determina",
        "cntSettoreProponenteLabel": "UFFICIO",
        "status": "PUBBLICATO",
    }


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

    def test_rejects_missing_or_malformed_results(self):
        for response in ({}, {"results": None}, {"results": ["not an object"]}):
            with self.subTest(response=response), self.assertRaises(RuntimeError):
                apt_cron.parse_source_response(response)


def quoted_part(message):
    return message.split(apt_cron.QUOTE_OPEN, 1)[1].split(apt_cron.QUOTE_CLOSE, 1)[0]


class FormatMessageTest(unittest.TestCase):
    def test_formats_a_readable_html_message(self):
        notice = first_notice()
        # Production enriches notices with attachment links before formatting.
        attachments = json.loads(ATTACHMENT_FIXTURE.read_text(encoding="utf-8"))
        links = apt_cron.fetch_attachments(
            FakeTransport(attachments),
            "https://example.test/api/pap/files",
            notice["id"],
        )
        notice.update(links)

        message = apt_cron.format_message(
            notice,
            "https://siopi.publisys.it/sito-aptbasilicata/albo-pretorio/dettaglio",
        )

        self.assertEqual(
            message,
            "\n".join(
                [
                    "<b>Nuovo atto APT Basilicata</b>",
                    "<u>Atto 244/2026</u>",
                    '<a href="https://siopi.publisys.it/sito-aptbasilicata/albo-pretorio/dettaglio/791962">Atto ufficiale</a>',
                    '<a href="https://example.test/katti/public/pap/edoc/download/unico/6500/791962">PDF ufficiale</a>',
                    '<a href="https://example.test/katti/public/pap/edoc/download/single/6500/791962/abc/notice.pdf">Allegato</a>',
                    '<a href="https://example.test/katti/public/pap/edoc/download/single/6500/791962/def/non-pdf.png">Allegato</a>',
                    "<b>Titolo:</b> Affidamento diretto per la sala espositiva",
                    "<b>Pubblicato il:</b> 25/11/2026",
                    "<b>Scade il:</b> 10/12/2026",
                    "#Delibera_del_Direttore_Generale #UFFICIO_AMMINISTRAZIONE",
                    "<b>Stato:</b> PUBBLICATO",
                    "<blockquote expandable>ID: 791962</blockquote>",
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

        quote = quoted_part(message)
        self.assertIn("Titolo:</b> Affidamento diretto per la sala espositiva", message)
        self.assertIn("#UFFICIO_AMMINISTRAZIONE", message)
        for name in apt_cron.NOTICE_FIELDS:
            if name in apt_cron.MESSAGE_MAIN_FIELDS:
                continue
            self.assertIn(f"{apt_cron.FIELD_LABELS[name]}: {notice[name]}", quote)
        self.assertIn('href="https://example.test/documento.pdf">PDF ufficiale</a>', message)
        self.assertIn('href="https://example.test/allegato.pdf">Allegato</a>', message)
        self.assertNotIn("Scadenza: non nota", message)
        for name in EXCLUDED_SOURCE_FIELDS:
            self.assertNotIn(name, message)
        self.assertNotIn("PRIVATE", message)
        self.assertLessEqual(len(message), apt_cron.TELEGRAM_TEXT_LIMIT)

    def test_escapes_every_dynamic_value(self):
        notice = first_notice()
        notice.update(
            title='Affidamento <b>&"x"</b>',
            status="<script>",
            cntNumeroGara='gara <&"1">',
            detail_url='https://example.test/dettaglio?a=1&b="2"',
        )

        message = apt_cron.format_message(notice, "https://example.test/dettaglio")

        self.assertIn(
            "<b>Titolo:</b> Affidamento &lt;b&gt;&amp;&quot;x&quot;&lt;/b&gt;", message
        )
        self.assertIn("<b>Stato:</b> &lt;script&gt;", message)
        self.assertIn("Numero gara: gara &lt;&amp;&quot;1&quot;&gt;", message)
        self.assertIn(
            'href="https://example.test/dettaglio?a=1&amp;b=&quot;2&quot;"', message
        )
        self.assertNotIn("<script>", message)
        self.assertNotIn('"x"</b>', message)

    def test_states_an_unknown_expiry_inside_the_quote(self):
        notice = first_notice()
        notice.update(expires=None, cntNumeroGara="123")

        message = apt_cron.format_message(notice, "https://example.test/dettaglio")

        self.assertNotIn("Scade il", message)
        self.assertEqual(
            quoted_part(message), "Scadenza: non nota\nID: 791962\nNumero gara: 123"
        )

    def test_keeps_the_document_date_when_the_source_provides_it(self):
        notice = first_notice()
        notice["cntDataDocumentoOrigine"] = "2026-11-20"

        message = apt_cron.format_message(notice, "https://example.test/dettaglio")

        self.assertIn("<b>Documento del:</b> 20/11/2026", message)
        self.assertNotIn("Data documento di origine:", message)

        notice["cntDataDocumentoOrigine"] = "non una data"
        self.assertIn(
            "<b>Documento del:</b> non una data",
            apt_cron.format_message(notice, "https://example.test/dettaglio"),
        )

    def test_new_act_is_the_default_headline(self):
        message = apt_cron.format_message(
            first_notice(), "https://example.test/albo-pretorio/dettaglio"
        )

        self.assertTrue(message.startswith("<b>Nuovo atto APT Basilicata</b>\n"))

    def test_updated_act_headline_is_unchanged(self):
        message = apt_cron.format_message(
            first_notice(), "https://example.test/albo-pretorio/dettaglio", updated=True
        )

        self.assertTrue(message.startswith("<b>Atto aggiornato APT Basilicata</b>\n"))

    def test_archived_act_headline(self):
        message = apt_cron.format_message(
            first_notice(), "https://example.test/albo-pretorio/dettaglio", archived=True
        )

        self.assertTrue(message.startswith("<b>Atto archiviato APT Basilicata</b>\n"))

    def test_expired_headline_wins_over_archived_for_a_scaduto_status(self):
        notice = first_notice()
        notice["status"] = "SCADUTO"

        message = apt_cron.format_message(
            notice, "https://example.test/albo-pretorio/dettaglio", archived=True
        )

        self.assertTrue(message.startswith("<b>Atto scaduto APT Basilicata</b>\n"))

    def test_expired_headline_when_the_expiry_is_before_today(self):
        notice = first_notice()
        notice["expires"] = "2026-12-10"
        base = "https://example.test/albo-pretorio/dettaglio"

        expired = apt_cron.format_message(notice, base, archived=True, today="2026-12-11")
        same_day = apt_cron.format_message(notice, base, archived=True, today="2026-12-10")
        notice["expires"] = "non una data"
        unparsable = apt_cron.format_message(notice, base, archived=True, today="2026-12-11")

        self.assertTrue(expired.startswith("<b>Atto scaduto APT Basilicata</b>\n"))
        self.assertTrue(same_day.startswith("<b>Atto archiviato APT Basilicata</b>\n"))
        self.assertTrue(unparsable.startswith("<b>Atto archiviato APT Basilicata</b>\n"))

    def test_updated_headline_wins_over_expired_and_archived(self):
        notice = first_notice()
        notice["status"] = "SCADUTO"

        message = apt_cron.format_message(
            notice,
            "https://example.test/albo-pretorio/dettaglio",
            updated=True,
            archived=True,
            today="2030-01-01",
        )

        self.assertTrue(message.startswith("<b>Atto aggiornato APT Basilicata</b>\n"))


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

    def test_archive_requires_a_valid_total_page_count(self):
        for response in ({"results": []}, {"results": [], "totalPages": 0}, {"results": [], "totalPages": "1"}):
            with self.subTest(response=response), self.assertRaises(RuntimeError):
                apt_cron.fetch_notices(
                    FakeTransport(response),
                    "https://example.test/filter",
                    "2026-11-25",
                    "1",
                    20,
                    archive=True,
                )


class PagedSourceTransport:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def request(self, method, url, payload=None):
        self.calls.append({"method": method, "url": url, "payload": payload})
        page = int(url.split("page=", 1)[1].split("&", 1)[0])
        if page >= len(self.pages):
            # The source answers 404 past the last page, so a walk never reaches this branch.
            raise RuntimeError("HTTP Error 404: Not Found")
        return self.pages[page]


class ArchiveQueryTest(unittest.TestCase):
    def test_archive_criteria_omit_the_publication_window(self):
        transport = FakeTransport({"results": [], "totalPages": 1})

        apt_cron.fetch_notices(
            transport,
            "https://example.test/filter",
            "2026-11-25",
            "200152",
            20,
            archive=True,
        )

        self.assertEqual(
            transport.calls[0]["payload"],
            {
                "dataOption": "all",
                "papSearchCriteriaList": [
                    {"filterKey": "cntNaturaAtto", "operation": "eq", "value": "200152"},
                    {"filterKey": "cntExternalStatus", "operation": "nu", "value": ""},
                    {"filterKey": "cntNumeroPap", "operation": "nn"},
                    {"filterKey": "cntAnnoNumeroPap", "operation": "nn"},
                ],
            },
        )

    def test_archive_pagination_walks_every_page_and_stops_before_a_404(self):
        transport = PagedSourceTransport(
            [
                {"results": [archive_item(1, "2026-11-25", 246)], "totalPages": 3},
                {"results": [archive_item(2, "2026-11-24", 245)], "totalPages": 3},
                {"results": [archive_item(3, "2026-11-23", 244)], "totalPages": 3},
            ]
        )

        notices = apt_cron.fetch_notices(
            transport,
            "https://example.test/filter",
            "2026-11-25",
            "200152",
            20,
            archive=True,
        )

        self.assertEqual([notice["id"] for notice in notices], [1, 2, 3])
        self.assertEqual(
            [call["url"] for call in transport.calls],
            [f"https://example.test/filter?page={page}&size=20" for page in range(3)],
        )

    def test_current_window_still_reads_only_page_zero(self):
        transport = PagedSourceTransport(
            [{"results": [archive_item(1, "2026-11-25", 246)], "totalPages": 5}]
        )

        notices = apt_cron.fetch_notices(
            transport,
            "https://example.test/filter",
            "2026-11-25",
            "200152",
            20,
        )

        self.assertEqual(len(notices), 1)
        self.assertEqual(
            [call["url"] for call in transport.calls],
            ["https://example.test/filter?page=0&size=20"],
        )


class PublishMessageTest(unittest.TestCase):
    def test_posts_html_to_telegram(self):
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
            {"chat_id": "@test_channel", "text": "test text", "parse_mode": "HTML"},
        )

    def test_rejects_a_telegram_error(self):
        transport = FakeTransport({"ok": False, "description": "chat not found"})

        with self.assertRaises(RuntimeError):
            apt_cron.publish_message(transport, "https://api.telegram.org/botTEST_TOKEN/sendMessage", "@x", "hi")


class SyntheticTelegramHtmlValidationTest(unittest.TestCase):
    """Validate the Destination channel message using only synthetic input and a fake transport."""

    TELEGRAM_URL = "https://api.telegram.invalid/botFAKE_TOKEN/sendMessage"
    DETAIL_BASE = "https://example.test/albo-pretorio/dettaglio"
    CHAT_ID = "@test_channel"
    TAG_RE = re.compile(r"</?[A-Za-z][A-Za-z0-9]*(?:\s[^<>]*)?>")
    ALLOWED_TAGS = {"a", "b", "blockquote", "u"}

    def synthetic_notice(self, **overrides):
        notice = {
            "id": 791962,
            "title": "Affidamento diretto per la sala espositiva",
            "category": "Delibera del Direttore Generale",
            "sector": "UFFICIO AMMINISTRAZIONE",
            "published": "2026-11-25",
            "expires": "2026-12-10",
            "year": 2026,
            "number": 244,
            "status": "PUBBLICATO",
            "cntNumeroGara": "gara 1",
            "detail_url": f"{self.DETAIL_BASE}/791962",
            "document_url": (
                "https://example.test/katti/public/pap/edoc/download/unico/6500/791962"
            ),
            "attachment_urls": [
                "https://example.test/katti/public/pap/edoc/download/single/6500/791962/abc/notice.pdf",
                "https://example.test/katti/public/pap/edoc/download/single/6500/791962/def/non-pdf.png",
            ],
        }
        notice.update(overrides)
        return notice

    def assert_balanced_html(self, text):
        stack = []
        for match in self.TAG_RE.finditer(text):
            tag = match.group(0)
            if tag.startswith("</"):
                name = tag[2:-1]
                self.assertTrue(stack, f"unexpected closing tag: {tag}")
                self.assertEqual(stack.pop(), name, f"unexpected closing tag: {tag}")
                continue
            name = tag[1:].split(None, 1)[0].rstrip(">")
            self.assertIn(name, self.ALLOWED_TAGS, f"unexpected tag: {tag}")
            stack.append(name)
        self.assertEqual(stack, [], f"unclosed tags: {stack}")
        without_tags = self.TAG_RE.sub("", text)
        self.assertNotIn("<", without_tags)
        self.assertNotIn(">", without_tags)

    def test_publish_message_sends_parse_mode_html_with_a_formatted_message(self):
        notice = self.synthetic_notice()
        message = apt_cron.format_message(notice, self.DETAIL_BASE)
        transport = FakeTransport({"ok": True, "result": {"message_id": 42}})

        result = apt_cron.publish_message(transport, self.TELEGRAM_URL, self.CHAT_ID, message)

        self.assertEqual(result, {"message_id": 42})
        self.assertEqual(len(transport.calls), 1)
        call = transport.calls[0]
        self.assertEqual(call["method"], "POST")
        self.assertEqual(call["url"], self.TELEGRAM_URL)
        self.assertEqual(
            call["payload"],
            {"chat_id": self.CHAT_ID, "text": message, "parse_mode": "HTML"},
        )
        self.assertEqual(
            message.splitlines()[:3],
            [
                "<b>Nuovo atto APT Basilicata</b>",
                "<u>Atto 244/2026</u>",
                f'<a href="{self.DETAIL_BASE}/791962">Atto ufficiale</a>',
            ],
        )
        self.assertIn("<b>Titolo:</b> Affidamento diretto per la sala espositiva", message)
        self.assert_balanced_html(message)

    def test_hostile_dynamic_values_are_escaped_without_raw_tags(self):
        notice = self.synthetic_notice(
            title='Affidamento <script>alert("x")</script> & <img src=x onerror=1>',
            status="</b></u><svg/onload=alert(1)>",
            cntNumeroGara='gara ">&<b>injected</b>',
            detail_url='https://example.test/dettaglio?a=1&b="2"><script>evil()</script>',
            document_url='https://example.test/doc.pdf?x="<img src=y>',
            attachment_urls=["https://example.test/allegato.png?y=<svg onload=1>"],
            category="<script>cat</script>",
            sector='"&sector"',
        )

        message = apt_cron.format_message(notice, self.DETAIL_BASE)

        self.assertIn(
            "<b>Titolo:</b> Affidamento &lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt; "
            "&amp; &lt;img src=x onerror=1&gt;",
            message,
        )
        self.assertIn(
            "<b>Stato:</b> &lt;/b&gt;&lt;/u&gt;&lt;svg/onload=alert(1)&gt;", message
        )
        self.assertIn(
            "Numero gara: gara &quot;&gt;&amp;&lt;b&gt;injected&lt;/b&gt;", message
        )
        self.assertIn(
            'href="https://example.test/dettaglio?a=1&amp;b=&quot;2&quot;&gt;'
            "&lt;script&gt;evil()&lt;/script&gt;",
            message,
        )
        for raw in (
            "<script>",
            "<img src=x",
            "<svg",
            "<b>injected</b>",
            "</b></u>",
            'b="2"><script>',
        ):
            self.assertNotIn(raw, message)
        self.assert_balanced_html(message)

    def test_long_hostile_values_stay_bounded_with_balanced_tags(self):
        hostile = '<script>"&' + "x" * 600
        notice = self.synthetic_notice(
            title=hostile,
            status="</blockquote><b>" + "y" * 600,
            cntNumeroGara=hostile * 10,
            cntExternalOggetto="<img src=x onerror=1>" * 50,
            detail_url="https://example.test/dettaglio?token=" + "a" * 5000,
            document_url="https://example.test/doc?token=" + "b" * 5000,
            attachment_urls=[
                f"https://example.test/allegato-{index}?token=" + "c" * 5000
                for index in range(10)
            ],
        )

        message = apt_cron.format_message(notice, self.DETAIL_BASE)

        self.assertGreater(len(message), 0)
        self.assertLessEqual(len(message), apt_cron.TELEGRAM_TEXT_LIMIT)
        self.assertIn(apt_cron.QUOTE_OPEN, message)
        self.assertTrue(message.endswith(apt_cron.QUOTE_CLOSE))
        self.assert_balanced_html(message)
        self.assertNotIn("<script>", message)
        self.assertNotIn("<img src=x", message)

    def test_official_pdf_and_non_pdf_attachment_links_are_rendered(self):
        notice = self.synthetic_notice(
            detail_url=None,
            document_url="https://example.test/documento-unico.pdf",
            attachment_urls=[
                "https://example.test/allegato.pdf",
                "https://example.test/allegato.png",
            ],
        )

        message = apt_cron.format_message(notice, "https://example.test/other-base")

        self.assertIn(
            '<a href="https://example.test/other-base/791962">Atto ufficiale</a>', message
        )
        self.assertIn(
            '<a href="https://example.test/documento-unico.pdf">PDF ufficiale</a>', message
        )
        self.assertIn('<a href="https://example.test/allegato.pdf">Allegato</a>', message)
        self.assertIn('<a href="https://example.test/allegato.png">Allegato</a>', message)
        self.assertEqual(message.count(">Allegato</a>"), 2)
        self.assertNotIn("link non disponibile", message)
        self.assert_balanced_html(message)


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


DOCUMENT_BYTES = b"%PDF-1.4 in-memory document payload"


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

    def fetch_bytes(self, url):
        self.calls.append({"method": "GET", "url": url, "payload": None})
        return DOCUMENT_BYTES

    def send_document(self, url, fields, filename, content):
        self.calls.append(
            {
                "method": "POST",
                "url": url,
                "payload": fields,
                "filename": filename,
                "content": content,
            }
        )
        return self.telegram_response


class FailingAttachmentTransport(SequenceTransport):
    def request(self, method, url, payload=None):
        if url.endswith("/api/pap/files/791962"):
            raise RuntimeError("temporary attachment failure")
        return super().request(method, url, payload)


class FailingArchiveDocumentTransport(SequenceTransport):
    def send_document(self, url, fields, filename, content):
        if fields.get("caption") == "PDF ufficiale: Atto 243/2026":
            raise RuntimeError("temporary document failure")
        return super().send_document(url, fields, filename, content)


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

    def test_first_run_writes_state_once(self):
        response = json.loads(FIXTURE.read_text(encoding="utf-8"))
        transport = SequenceTransport(response, {"ok": True, "result": {"message_id": 1}})
        with tempfile.TemporaryDirectory() as directory:
            config = run_config(Path(directory) / "state.json")
            with mock.patch("apt_cron.save_state", wraps=apt_cron.save_state) as saved:
                apt_cron.run_once(transport, config)

        self.assertEqual(saved.call_count, 1)

    def test_a_regular_run_keeps_the_new_headline_and_never_marks_acts_archived(self):
        response = json.loads(FIXTURE.read_text(encoding="utf-8"))
        transport = SequenceTransport(response, {"ok": True, "result": {"message_id": 1}})
        with tempfile.TemporaryDirectory() as directory:
            config = run_config(Path(directory) / "state.json")
            apt_cron.run_once(transport, config)
            response["results"][0]["status"] = "SCADUTO"
            transport.calls.clear()

            apt_cron.run_once(transport, config)
            headlines = [
                call["payload"]["text"].splitlines()[0]
                for call in transport.calls
                if "sendMessage" in call["url"]
            ]

        self.assertEqual(headlines, ["<b>Atto aggiornato APT Basilicata</b>"])

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
        self.assertEqual(len(telegram_calls), 4)
        self.assertIn("Atto aggiornato APT Basilicata", telegram_calls[0]["payload"]["text"])
        self.assertIn("Titolo aggiornato", telegram_calls[0]["payload"]["text"])
        self.assertIn("sendDocument", telegram_calls[1]["url"])
        self.assertIn("sendDocument", telegram_calls[2]["url"])
        self.assertIn("sendDocument", telegram_calls[3]["url"])
        self.assertEqual(telegram_calls[1]["payload"]["caption"], "PDF ufficiale: Atto 244/2026")

    def test_notice_without_documents_publishes_only_the_message(self):
        response = json.loads(FIXTURE.read_text(encoding="utf-8"))
        transport = SequenceTransport(
            response,
            {"ok": True, "result": {"message_id": 1}},
            {"error": False, "results": []},
        )
        with tempfile.TemporaryDirectory() as directory:
            config = run_config(Path(directory) / "state.json")
            apt_cron.run_once(transport, config)
            response["results"][0]["cntTitle"] = "Titolo aggiornato"
            transport.calls.clear()

            apt_cron.run_once(transport, config)

        sent = [call for call in transport.calls if "api.telegram.org" in call["url"]]
        self.assertEqual(len(sent), 1)
        self.assertIn("sendMessage", sent[0]["url"])

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
            # The changed notice also re-reads its PDF links; nothing reaches Telegram.
            self.assertEqual(
                [call["url"] for call in transport.calls if "api.telegram.org" in call["url"]],
                [],
            )
            self.assertTrue(apt_cron.load_state(config["state_path"]))


class BackfillHeadlineTest(unittest.TestCase):
    def test_backfill_labels_the_whole_history_as_archived(self):
        response = json.loads(FIXTURE.read_text(encoding="utf-8"))
        response["totalPages"] = 1
        transport = SequenceTransport(response, {"ok": True, "result": {"message_id": 1}})
        with tempfile.TemporaryDirectory() as directory:
            config = run_config(Path(directory) / "state.json")
            config["archive"] = True

            stats = apt_cron.run_once(transport, config)
            headlines = [
                call["payload"]["text"].splitlines()[0]
                for call in transport.calls
                if "sendMessage" in call["url"]
            ]

        self.assertEqual(stats["published"], 2)
        self.assertEqual(headlines, ["<b>Atto archiviato APT Basilicata</b>"] * 2)

    def test_backfill_says_expired_when_the_expiry_is_before_today(self):
        response = json.loads(FIXTURE.read_text(encoding="utf-8"))
        response["totalPages"] = 1
        response["results"][0]["cntDataFinePubblicazione"] = "2026-11-01"
        response["results"][1]["cntDataInizioPubblicazione"] = "2026-11-20"
        transport = SequenceTransport(response, {"ok": True, "result": {"message_id": 1}})
        with tempfile.TemporaryDirectory() as directory:
            config = run_config(Path(directory) / "state.json")
            config["archive"] = True

            apt_cron.run_once(transport, config)
            headlines = [
                call["payload"]["text"].splitlines()[0]
                for call in transport.calls
                if "sendMessage" in call["url"]
            ]

        self.assertEqual(
            headlines,
            [
                "<b>Atto archiviato APT Basilicata</b>",
                "<b>Atto scaduto APT Basilicata</b>",
            ],
        )


class PublicationOrderTest(unittest.TestCase):
    def test_orders_notices_oldest_first_and_the_newest_act_last(self):
        changes = [
            (archive_item(1, "2026-11-25", 246), False),
            (archive_item(2, "2026-11-24", 245), False),
            (archive_item(3, "2026-11-20", 244), False),
        ]

        ordered = apt_cron.publication_order(changes)

        self.assertEqual([notice["id"] for notice, _ in ordered], [3, 2, 1])

    def test_acts_published_the_same_day_keep_the_source_order_reversed(self):
        changes = [
            (archive_item(1, "2026-11-25", 246), False),
            (archive_item(2, "2026-11-25", 245), False),
        ]

        ordered = apt_cron.publication_order(changes)

        self.assertEqual([notice["id"] for notice, _ in ordered], [2, 1])

    def test_run_once_publishes_oldest_first_so_the_newest_act_is_the_last_message(self):
        response = {
            "results": [
                archive_item(800003, "2026-11-25", 246),
                archive_item(800002, "2026-11-24", 245),
                archive_item(800001, "2026-11-20", 244),
            ]
        }
        transport = SequenceTransport(response, {"ok": True, "result": {"message_id": 1}})
        with tempfile.TemporaryDirectory() as directory:
            config = run_config(Path(directory) / "state.json")
            apt_cron.run_once(transport, config)
            for item in response["results"]:
                item["cntTitle"] += " aggiornato"
            transport.calls.clear()

            stats = apt_cron.run_once(transport, config)
            messages = [
                call["payload"]["text"]
                for call in transport.calls
                if "sendMessage" in call["url"]
            ]

        self.assertEqual(stats["published"], 3)
        self.assertEqual(
            [
                line
                for message in messages
                for line in message.splitlines()
                if line.startswith("<b>Pubblicato il:</b> ")
            ],
            [
                "<b>Pubblicato il:</b> 20/11/2026",
                "<b>Pubblicato il:</b> 24/11/2026",
                "<b>Pubblicato il:</b> 25/11/2026",
            ],
        )


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
            # Publication runs oldest first, so the newest act is the one that fails here.
            old_fingerprint = initial_state["notices"]["791962"]
            for item in response["results"]:
                item["cntTitle"] += " aggiornato"
            transport.calls.clear()

            with self.assertRaises(RuntimeError):
                apt_cron.run_once(transport, config)
            state = apt_cron.load_state(config["state_path"])

        self.assertEqual(transport.telegram_calls, 2)
        self.assertNotEqual(state["notices"]["791960"], initial_state["notices"]["791960"])
        self.assertEqual(state["notices"]["791962"], old_fingerprint)


class BackfillTest(unittest.TestCase):
    def backfill_transport(self, response):
        source_response = dict(response)
        source_response.setdefault("totalPages", 1)
        return SequenceTransport(
            source_response, {"ok": True, "result": {"message_id": 1}}, {"results": []}
        )

    def test_backfill_publishes_notices_seeded_by_a_normal_run(self):
        response = json.loads(FIXTURE.read_text(encoding="utf-8"))
        response["totalPages"] = 1
        transport = SequenceTransport(response, {"ok": True, "result": {"message_id": 1}})
        with tempfile.TemporaryDirectory() as directory:
            config = run_config(Path(directory) / "state.json")
            apt_cron.run_once(transport, config)
            config["archive"] = True
            transport.calls.clear()

            stats = apt_cron.run_once(transport, config)
            messages = [
                call["payload"]["text"]
                for call in transport.calls
                if "sendMessage" in call["url"]
            ]
            state = apt_cron.load_state(config["state_path"])

        self.assertEqual(stats["published"], 2)
        self.assertEqual(
            [message.splitlines()[0] for message in messages],
            ["<b>Atto archiviato APT Basilicata</b>", "<b>Atto archiviato APT Basilicata</b>"],
        )
        self.assertEqual(set(state["sent_messages"]), {"791962", "791960"})

    def test_backfill_continues_when_one_attachment_lookup_fails(self):
        response = json.loads(FIXTURE.read_text(encoding="utf-8"))
        response["totalPages"] = 1
        transport = FailingAttachmentTransport(response, {"ok": True, "result": {"message_id": 1}})
        with tempfile.TemporaryDirectory() as directory:
            config = run_config(Path(directory) / "state.json")
            config["archive"] = True

            stats = apt_cron.run_once(transport, config)
            state = apt_cron.load_state(config["state_path"])
            messages = [call for call in transport.calls if "sendMessage" in call["url"]]

        self.assertEqual(stats, {"notices": 2, "published": 1, "dry_run": False, "attachment_errors": 1})
        self.assertEqual(len(messages), 1)
        self.assertNotIn("791962", state["notices"])
        self.assertEqual(set(state["sent_messages"]), {"791960"})

    def test_backfill_continues_when_one_document_upload_fails_and_retries_it(self):
        response = json.loads(FIXTURE.read_text(encoding="utf-8"))
        response["totalPages"] = 1
        transport = FailingArchiveDocumentTransport(response, {"ok": True, "result": {"message_id": 1}})
        with tempfile.TemporaryDirectory() as directory:
            config = run_config(Path(directory) / "state.json")
            config["archive"] = True

            stats = apt_cron.run_once(transport, config)
            state = apt_cron.load_state(config["state_path"])
            transport.calls.clear()

            retry_transport = SequenceTransport(response, {"ok": True, "result": {"message_id": 1}})
            retry_stats = apt_cron.run_once(retry_transport, config)
            retry_state = apt_cron.load_state(config["state_path"])
            retry_messages = [call for call in retry_transport.calls if "sendMessage" in call["url"]]

        self.assertEqual(stats["published"], 2)
        self.assertEqual(stats["document_errors"], 1)
        self.assertEqual(set(state["sent_messages"]), {"791962", "791960"})
        self.assertNotIn("791960", state["notices"])
        self.assertIn("791962", state["notices"])
        self.assertEqual(retry_stats["published"], 0)
        self.assertEqual(retry_messages, [])
        self.assertEqual(set(retry_state["notices"]), {"791962", "791960"})

    def test_backfill_publishes_the_archive_oldest_first_without_writing_the_index(self):
        response = {
            "results": [
                archive_item(800003, "2026-11-25", 246),
                archive_item(800002, "2026-11-20", 243),
                archive_item(800001, "2026-09-01", 12),
            ]
        }
        transport = self.backfill_transport(response)
        with tempfile.TemporaryDirectory() as directory:
            config = run_config(Path(directory) / "state.json")
            config["archive"] = True

            stats = apt_cron.run_once(transport, config)

            source_calls = [
                call for call in transport.calls if call["url"].startswith(config["source_url"])
            ]
            documents = [call for call in transport.calls if "sendDocument" in call["url"]]
            messages = [
                call["payload"]["text"]
                for call in transport.calls
                if "sendMessage" in call["url"]
            ]
            index_exists = Path(config["index_dir"]).exists()
            state = apt_cron.load_state(config["state_path"])

        self.assertEqual(stats, {"notices": 3, "published": 3, "dry_run": False})
        self.assertEqual(
            [call["url"] for call in source_calls],
            [f"{config['source_url']}?page=0&size=20"],
        )
        self.assertNotIn("cntDataInizioPubblicazione", json.dumps(source_calls[0]["payload"]))
        self.assertFalse(index_exists)
        self.assertEqual(len(messages), 3)
        self.assertEqual(
            [
                line
                for message in messages
                for line in message.splitlines()
                if line.startswith("<b>Pubblicato il:</b> ")
            ],
            [
                "<b>Pubblicato il:</b> 01/09/2026",
                "<b>Pubblicato il:</b> 20/11/2026",
                "<b>Pubblicato il:</b> 25/11/2026",
            ],
        )
        self.assertFalse([line for message in messages for line in message.splitlines() if line.startswith("PDF: ")])
        self.assertEqual(documents, [])
        self.assertEqual(set(state["notices"]), {"800001", "800002", "800003"})

    def test_rerunning_backfill_does_not_republish_unchanged_notices(self):
        response = {
            "results": [
                archive_item(800002, "2026-11-20", 243),
                archive_item(800001, "2026-09-01", 12),
            ]
        }
        transport = self.backfill_transport(response)
        with tempfile.TemporaryDirectory() as directory:
            config = run_config(Path(directory) / "state.json")
            config["archive"] = True
            apt_cron.run_once(transport, config)
            transport.calls.clear()

            stats = apt_cron.run_once(transport, config)

        self.assertEqual(stats["published"], 0)
        self.assertEqual([call for call in transport.calls if "api.telegram.org" in call["url"]], [])

    def test_cli_backfill_reads_the_archive_and_writes_no_index(self):
        response = {
            "results": [
                archive_item(800002, "2026-11-25", 246),
                archive_item(800001, "2026-09-01", 12),
            ]
        }
        transport = self.backfill_transport(response)
        with tempfile.TemporaryDirectory() as directory:
            config = run_config(Path(directory) / "state.json")
            argv = [
                "--backfill",
                "--state-path",
                config["state_path"],
                "--index-dir",
                config["index_dir"],
                "--source-url",
                config["source_url"],
                "--attachments-base",
                config["attachments_base"],
            ]
            with mock.patch.dict(
                os.environ,
                {"TELEGRAM_BOT_TOKEN": "TEST_TOKEN", "TELEGRAM_CHAT_ID": "@test_channel"},
            ), mock.patch.object(apt_cron, "UrllibTransport", lambda: transport), mock.patch(
                "sys.stdout", new_callable=io.StringIO
            ) as stdout:
                code = apt_cron.main(argv)

            index_exists = Path(config["index_dir"]).exists()

        self.assertEqual(code, 0)
        self.assertFalse(index_exists)
        self.assertEqual(json.loads(stdout.getvalue())["published"], 2)


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

        self.assertEqual(len(documents), 3)
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
        # No document was ever sent for this legacy state, so no text message is assumed either.
        self.assertEqual(migrated["sent_messages"], {})

    def test_migrates_a_legacy_state_that_already_tracked_documents(self):
        legacy = {
            "version": 1,
            "notices": {"791962": "old-fingerprint"},
            "sent_documents": {"https://example.test/a.pdf": "791962"},
        }

        migrated = apt_cron.migrate_state(legacy)

        self.assertEqual(migrated["sent_messages"], {"791962": "old-fingerprint"})

    def test_legacy_seeded_state_does_not_upload_documents_without_a_message(self):
        response = json.loads(FIXTURE.read_text(encoding="utf-8"))
        transport = SequenceTransport(response, {"ok": True, "result": {"message_id": 1}})
        with tempfile.TemporaryDirectory() as directory:
            config = run_config(Path(directory) / "state.json")
            apt_cron.run_once(transport, config)
            seeded = apt_cron.load_state(config["state_path"])
            legacy = {"version": 1, "notices": seeded["notices"], "attachments": seeded["attachments"]}
            apt_cron.save_state(config["state_path"], legacy)
            transport.calls.clear()

            stats = apt_cron.run_once(transport, config)

        self.assertEqual(stats["published"], 0)
        self.assertEqual([call for call in transport.calls if "api.telegram.org" in call["url"]], [])

    def test_falls_back_to_detail_url_when_id_is_missing(self):
        notice = {"detail_url": "https://example.test/albo-pretorio/dettaglio/999", "title": "x"}

        key = apt_cron.notice_key(notice)

        self.assertNotEqual(key, "None")
        self.assertEqual(key, apt_cron.notice_key(dict(notice, title="changed")))
        self.assertNotEqual(key, apt_cron.notice_key(dict(notice, detail_url="https://example.test/other")))


class StateRetentionTest(unittest.TestCase):
    def test_a_regular_run_keeps_historical_notice_fingerprints(self):
        response = json.loads(FIXTURE.read_text(encoding="utf-8"))
        transport = SequenceTransport(response, {"ok": True, "result": {"message_id": 1}})
        with tempfile.TemporaryDirectory() as directory:
            config = run_config(Path(directory) / "state.json")
            apt_cron.save_state(
                config["state_path"],
                {
                    "version": 2,
                    "notices": {"archived-1": "old-fingerprint"},
                    "attachments": {},
                    "sent_documents": {},
                    "sent_messages": {},
                },
            )

            apt_cron.run_once(transport, config)
            state = apt_cron.load_state(config["state_path"])

        self.assertEqual(state["notices"]["archived-1"], "old-fingerprint")
        self.assertEqual(set(state["notices"]), {"archived-1", "791962", "791960"})


class DocumentTransport:
    def __init__(self, content=DOCUMENT_BYTES, response=None):
        self.content = content
        self.response = response or {"ok": True, "result": {"message_id": 9}}
        self.fetched = []
        self.calls = []

    def fetch_bytes(self, url):
        self.fetched.append(url)
        return self.content

    def send_document(self, url, fields, filename, content):
        self.calls.append(
            {"url": url, "payload": fields, "filename": filename, "content": content}
        )
        return self.response


class PdfDeliveryTest(unittest.TestCase):
    def test_fetch_attachments_exposes_every_downloadable_attachment(self):
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
                    "https://example.test/katti/public/pap/edoc/download/single/6500/791962/abc/notice.pdf",
                    "https://example.test/katti/public/pap/edoc/download/single/6500/791962/def/non-pdf.png",
                ],
            },
        )

    def test_fetch_attachments_ignores_non_http_download_urls(self):
        response = {
            "error": False,
            "results": [
                {
                    "documentoUnico": {
                        "mimeType": "application/pdf",
                        "downloadUrl": "data:application/pdf;base64,AAAA",
                    },
                    "files": [
                        {"mimeType": "application/pdf", "downloadUrl": "https://example.test/a.pdf"},
                        {"mimeType": "image/png", "downloadUrl": "file:///tmp/a.png"},
                    ],
                }
            ],
        }

        links = apt_cron.fetch_attachments(
            FakeTransport(response), "https://example.test/api/pap/files", 791962
        )

        self.assertEqual(links, {"document_url": None, "attachment_urls": ["https://example.test/a.pdf"]})

    def test_absent_attachment_fields_are_empty_not_errors(self):
        response = {"results": [{"documentoUnico": None, "files": None}]}

        links = apt_cron.fetch_attachments(
            FakeTransport(response), "https://example.test/api/pap/files", 791962
        )

        self.assertEqual(links, {"document_url": None, "attachment_urls": []})

    def test_rejects_malformed_attachment_results(self):
        for response in (
            {},
            {"results": None},
            {"results": ["not an object"]},
            {"results": [{"documentoUnico": []}]},
            {"results": [{"documentoUnico": False}]},
            {"results": [{"documentoUnico": 0}]},
            {"results": [{"files": ""}]},
            {"results": [{"files": False}]},
            {"results": [{"files": 0}]},
            {"results": [{"files": "bad"}]},
        ):
            with self.subTest(response=response), self.assertRaises(RuntimeError):
                apt_cron.fetch_attachments(
                    FakeTransport(response), "https://example.test/api/pap/files", 791962
                )

    def test_fetches_the_pdf_bytes_and_uploads_them_as_a_document(self):
        transport = DocumentTransport()

        result = apt_cron.publish_document(
            transport,
            "https://api.telegram.org/botTEST_TOKEN/sendDocument",
            "@test_channel",
            "https://example.test/katti/public/pap/edoc/download/single/6500/791962/abc/Delibera.pdf",
            "PDF ufficiale",
        )

        self.assertEqual(result["message_id"], 9)
        self.assertEqual(
            transport.fetched,
            [
                "https://example.test/katti/public/pap/edoc/download/single/6500/791962/abc/Delibera.pdf"
            ],
        )
        self.assertEqual(
            transport.calls[0]["payload"],
            {"chat_id": "@test_channel", "caption": "PDF ufficiale"},
        )
        self.assertEqual(transport.calls[0]["filename"], "Delibera.pdf")
        self.assertEqual(transport.calls[0]["content"], DOCUMENT_BYTES)
        self.assertNotIn("https://example.test", json.dumps(transport.calls[0]["payload"]))

    def test_falls_back_to_a_pdf_name_when_the_url_has_no_file_name(self):
        transport = DocumentTransport()

        apt_cron.publish_document(
            transport,
            "https://api.telegram.org/botTEST_TOKEN/sendDocument",
            "@test_channel",
            "https://example.test/katti/public/pap/edoc/download/unico/6500/791962",
            "PDF ufficiale",
        )

        self.assertEqual(transport.calls[0]["filename"], "document.pdf")

    def test_rejects_a_document_above_the_size_bound_before_upload(self):
        transport = DocumentTransport(content=b"x" * 11)

        with mock.patch.object(apt_cron, "DOCUMENT_MAX_BYTES", 10), self.assertRaises(RuntimeError):
            apt_cron.publish_document(
                transport,
                "https://api.telegram.org/botTEST_TOKEN/sendDocument",
                "@x",
                "https://x/a.pdf",
                "c",
            )

        self.assertEqual(transport.calls, [])

    def test_rejects_a_document_error(self):
        transport = DocumentTransport(response={"ok": False, "description": "file too large"})

        with self.assertRaises(RuntimeError):
            apt_cron.publish_document(transport, "https://api.telegram.org/botTEST_TOKEN/sendDocument", "@x", "https://x/a.pdf", "c")


class UrlSchemeTest(unittest.TestCase):
    def test_fetch_bytes_refuses_a_non_http_url_before_opening_it(self):
        with mock.patch.object(apt_cron, "urlopen") as opened:
            with self.assertRaises(RuntimeError):
                apt_cron.UrllibTransport().fetch_bytes("file:///etc/apt-cron/albo.env")

        opened.assert_not_called()

    def test_message_does_not_render_unsafe_urls_as_links(self):
        notice = full_notice()
        notice.update(
            detail_url="javascript:alert(1)",
            document_url="data:application/pdf;base64,AAAA",
            attachment_urls=["file:///etc/apt-cron/albo.env"],
        )

        text = apt_cron.format_message(notice, "https://example.test/albo")

        self.assertNotIn("javascript:", text)
        self.assertNotIn('href="data:', text)
        self.assertNotIn("file:///", text)

    def test_index_does_not_render_unsafe_urls_as_links(self):
        notice = full_notice()
        notice.update(
            detail_url="javascript:alert(1)",
            document_url="data:text/html,<script>x</script>",
            attachment_urls=["file:///etc/apt-cron/albo.env"],
        )
        with tempfile.TemporaryDirectory() as directory:
            apt_cron.write_index(directory, apt_cron.build_index([notice]))
            html_text = (Path(directory) / "index.html").read_text(encoding="utf-8")
            markdown_text = (Path(directory) / "index.md").read_text(encoding="utf-8")

        for text in (html_text, markdown_text):
            self.assertNotIn("javascript:", text)
            self.assertNotIn("file:///", text)
            self.assertNotIn("data:text/html", text)


class InputHardeningTest(unittest.TestCase):
    def test_notice_key_falls_back_to_the_attachment_urls_field(self):
        notice = {"attachment_urls": ["https://example.test/a.pdf"]}

        key = apt_cron.notice_key(notice)

        self.assertNotEqual(key, "None")
        self.assertEqual(key, apt_cron.notice_key(dict(notice, title="changed")))

    def test_document_filename_cannot_inject_a_header(self):
        name = apt_cron.document_filename('https://example.test/a"b\r\nX-Evil: 1.pdf')

        for unsafe in ('"', "\r", "\n"):
            self.assertNotIn(unsafe, name)
        self.assertTrue(name.endswith(".pdf"))

    def test_multipart_body_infers_the_attachment_content_type(self):
        body, _ = apt_cron.multipart_body({"chat_id": "1"}, "attachment.png", b"data")

        self.assertIn(b"Content-Type: image/png", body)

    def test_multipart_headers_cannot_be_injected(self):
        body, _ = apt_cron.multipart_body(
            {"chat_id": "1\r\nX-Evil: 1"}, 'a"\r\nb.pdf', b"data"
        )

        self.assertNotIn(b"\r\nX-Evil", body)
        self.assertNotIn(b'filename="a"', body)
        self.assertIn(b'filename="a___b.pdf"', body)

    def test_save_state_removes_a_temporary_file_when_serialization_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            with mock.patch("apt_cron.json.dump", side_effect=TypeError("boom")):
                with self.assertRaises(TypeError):
                    apt_cron.save_state(str(path), {})

            self.assertEqual(list(Path(directory).iterdir()), [])


class UrllibDocumentUploadTest(unittest.TestCase):
    def test_posts_a_multipart_body_that_carries_the_bytes_not_the_url(self):
        captured = {}

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self, *args):
                return json.dumps({"ok": True, "result": {"message_id": 5}}).encode("utf-8")

        def fake_urlopen(request, timeout=None):
            captured["request"] = request
            captured["timeout"] = timeout
            return Response()

        with mock.patch.object(apt_cron, "urlopen", fake_urlopen):
            result = apt_cron.UrllibTransport().send_document(
                "https://api.telegram.org/botTEST_TOKEN/sendDocument",
                {"chat_id": "@test_channel", "caption": "PDF ufficiale"},
                "notice.pdf",
                DOCUMENT_BYTES,
            )

        request = captured["request"]
        headers = {name.lower(): value for name, value in request.header_items()}
        self.assertTrue(result["ok"])
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(captured["timeout"], apt_cron.DOCUMENT_UPLOAD_TIMEOUT)
        self.assertTrue(headers["content-type"].startswith("multipart/form-data; boundary="))
        boundary = headers["content-type"].split("boundary=", 1)[1].encode("utf-8")
        self.assertTrue(request.data.startswith(b"--" + boundary))
        self.assertTrue(request.data.endswith(b"--" + boundary + b"--\r\n"))
        self.assertIn(b"%PDF-1.4 in-memory document payload", request.data)
        self.assertIn(b'name="document"; filename="notice.pdf"', request.data)
        self.assertIn(b'name="chat_id"', request.data)
        self.assertIn(b"@test_channel", request.data)
        self.assertIn(b'name="caption"', request.data)
        self.assertNotIn(b"https://example.test", request.data)

    def test_reads_document_bytes_in_memory_with_the_existing_timeout(self):
        captured = {}

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self, amount=None):
                captured["amount"] = amount
                return DOCUMENT_BYTES

        def fake_urlopen(request, timeout=None):
            captured["timeout"] = timeout
            return Response()

        with mock.patch.object(apt_cron, "urlopen", fake_urlopen):
            content = apt_cron.UrllibTransport().fetch_bytes("https://example.test/a.pdf")

        self.assertEqual(content, DOCUMENT_BYTES)
        self.assertEqual(captured["timeout"], 20)
        self.assertEqual(captured["amount"], apt_cron.DOCUMENT_MAX_BYTES + 1)


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
                "https://example.test/katti/public/pap/edoc/download/single/6500/791962/abc/notice.pdf",
                "https://example.test/katti/public/pap/edoc/download/single/6500/791962/def/non-pdf.png",
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


class EnvFileTest(unittest.TestCase):
    def test_env_file_supplies_configuration_before_argparse(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / "albo.env"
            env_file.write_text("# local credentials\nexport APT_PAGE_SIZE=bogus\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {"APT_ENV_FILE": str(env_file)}), mock.patch(
                "sys.stderr", new_callable=io.StringIO
            ) as stderr:
                os.environ.pop("APT_PAGE_SIZE", None)
                with self.assertRaises(SystemExit) as exit_code:
                    apt_cron.main(["--dry-run"])

        self.assertEqual(exit_code.exception.code, 2)
        self.assertIn("APT_PAGE_SIZE must be a positive integer", stderr.getvalue())

    def test_existing_environment_value_wins_over_the_env_file(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / "albo.env"
            env_file.write_text("APT_PAGE_SIZE=7\nAPT_INDEX_DIR=from-file\n", encoding="utf-8")
            with mock.patch.dict(
                os.environ,
                {"APT_ENV_FILE": str(env_file), "APT_INDEX_DIR": "from-environment"},
            ):
                os.environ.pop("APT_PAGE_SIZE", None)

                apt_cron.load_env_file()

                self.assertEqual(os.environ["APT_PAGE_SIZE"], "7")
                self.assertEqual(os.environ["APT_INDEX_DIR"], "from-environment")


class TelegramProfileTest(unittest.TestCase):
    def test_production_profile_uses_the_production_credential_names(self):
        with mock.patch.dict(
            os.environ,
            {
                "TELEGRAM_BOT_TOKEN": "PRODUCTION_TOKEN",
                "TELEGRAM_CHAT_ID": "@production",
                "APT_TEST_TELEGRAM_BOT_TOKEN": "TEST_TOKEN",
                "APT_TEST_TELEGRAM_CHAT_ID": "@test",
            },
        ):
            self.assertEqual(
                apt_cron.telegram_credentials("production"),
                ("PRODUCTION_TOKEN", "@production"),
            )

    def test_test_profile_ignores_production_credentials(self):
        with mock.patch.dict(
            os.environ,
            {
                "TELEGRAM_BOT_TOKEN": "PRODUCTION_TOKEN",
                "TELEGRAM_CHAT_ID": "@production",
                "APT_TEST_TELEGRAM_BOT_TOKEN": "TEST_TOKEN",
                "APT_TEST_TELEGRAM_CHAT_ID": "@test",
            },
        ):
            self.assertEqual(
                apt_cron.telegram_credentials("test"), ("TEST_TOKEN", "@test")
            )

    def test_default_production_profile_reaches_the_fake_transport(self):
        captured = {}

        def run_once(transport, config):
            captured.update(config)
            return {}

        with mock.patch.dict(
            os.environ,
            {
                "APT_TELEGRAM_PROFILE": "",
                "TELEGRAM_BOT_TOKEN": "PRODUCTION_TOKEN",
                "TELEGRAM_CHAT_ID": "@production",
                "APT_TEST_TELEGRAM_BOT_TOKEN": "TEST_TOKEN",
                "APT_TEST_TELEGRAM_CHAT_ID": "@test",
            },
        ), mock.patch.object(apt_cron, "UrllibTransport", lambda: object()), mock.patch.object(
            apt_cron, "run_once", run_once
        ), mock.patch("sys.stdout", new_callable=io.StringIO):
            code = apt_cron.main(["--backfill"])

        self.assertEqual(code, 0)
        self.assertEqual(captured["telegram_profile"], "production")
        self.assertEqual(captured["chat_id"], "@production")
        self.assertIn("PRODUCTION_TOKEN", captured["telegram_url"])
        self.assertNotIn("TEST_TOKEN", captured["telegram_url"])

    def test_test_profile_reaches_the_fake_transport_with_test_credentials(self):
        captured = {}

        def run_once(transport, config):
            captured.update(config)
            return {}

        with mock.patch.dict(
            os.environ,
            {
                "APT_TELEGRAM_PROFILE": "test",
                "TELEGRAM_BOT_TOKEN": "PRODUCTION_TOKEN",
                "TELEGRAM_CHAT_ID": "@production",
                "APT_TEST_TELEGRAM_BOT_TOKEN": "TEST_TOKEN",
                "APT_TEST_TELEGRAM_CHAT_ID": "@test",
            },
        ), mock.patch.object(apt_cron, "UrllibTransport", lambda: object()), mock.patch.object(
            apt_cron, "run_once", run_once
        ), mock.patch("sys.stdout", new_callable=io.StringIO):
            code = apt_cron.main(["--backfill"])

        self.assertEqual(code, 0)
        self.assertEqual(captured["telegram_profile"], "test")
        self.assertEqual(captured["chat_id"], "@test")
        self.assertIn("TEST_TOKEN", captured["telegram_url"])
        self.assertNotIn("PRODUCTION_TOKEN", captured["telegram_url"])

    def test_missing_test_credentials_do_not_fall_back_to_production(self):
        with mock.patch.dict(
            os.environ,
            {
                "APT_TELEGRAM_PROFILE": "test",
                "TELEGRAM_BOT_TOKEN": "PRODUCTION_TOKEN",
                "TELEGRAM_CHAT_ID": "@production",
                "APT_TEST_TELEGRAM_BOT_TOKEN": "",
                "APT_TEST_TELEGRAM_CHAT_ID": "",
            },
        ), mock.patch("sys.stderr", new_callable=io.StringIO) as stderr:
            with self.assertRaises(SystemExit) as raised:
                apt_cron.main(["--backfill"])

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("APT_TEST_TELEGRAM_BOT_TOKEN", stderr.getvalue())
        self.assertIn("APT_TEST_TELEGRAM_CHAT_ID", stderr.getvalue())

    def test_unknown_profile_is_rejected(self):
        with mock.patch.dict(
            os.environ, {"APT_TELEGRAM_PROFILE": "staging"}
        ), mock.patch("sys.stderr", new_callable=io.StringIO) as stderr:
            with self.assertRaises(SystemExit) as raised:
                apt_cron.main(["--dry-run"])

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("APT_TELEGRAM_PROFILE must be one of", stderr.getvalue())


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
    def test_changed_notice_sends_the_pdf_and_every_attachment(self):
        response = json.loads(FIXTURE.read_text(encoding="utf-8"))
        transport = SequenceTransport(response, {"ok": True, "result": {"message_id": 1}})
        with tempfile.TemporaryDirectory() as directory:
            config = run_config(Path(directory) / "state.json")
            apt_cron.run_once(transport, config)
            response["results"][0]["cntTitle"] = "Titolo aggiornato"
            transport.calls.clear()

            apt_cron.run_once(transport, config)

        sent = [call for call in transport.calls if "api.telegram.org" in call["url"]]
        self.assertEqual(len(sent), 4)
        self.assertIn("sendMessage", sent[0]["url"])
        self.assertEqual(
            [call["filename"] for call in sent[1:]],
            ["document.pdf", "notice.pdf", "non-pdf.png"],
        )

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
        self.assertEqual(sent[1]["filename"], "documento-799999.pdf")
        self.assertEqual(sent[2]["filename"], "allegato-799999.pdf")
        self.assertEqual(sent[1]["content"], DOCUMENT_BYTES)
        self.assertEqual(sent[2]["content"], DOCUMENT_BYTES)
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


class CountingAttachmentsTransport(SequenceTransport):
    def __init__(self, source_response, telegram_response):
        super().__init__(source_response, telegram_response)
        self.attachment_requests = []

    def request(self, method, url, payload=None):
        if "/api/pap/files/" in url:
            self.attachment_requests.append(url.rsplit("/", 1)[1])
        return super().request(method, url, payload)


NEW_PDF = {
    "tipoFile": "ALLEGATO",
    "mimeType": "application/pdf",
    "title": "integrazione.pdf",
    "downloadUrl": "https://example.test/katti/public/pap/edoc/download/single/6500/791962/ghi/integrazione.pdf",
    "position": 2,
}


class AttachmentCacheRefreshTest(unittest.TestCase):
    def test_changed_notice_refreshes_its_cached_pdf_links(self):
        response = json.loads(FIXTURE.read_text(encoding="utf-8"))
        transport = CountingAttachmentsTransport(
            response, {"ok": True, "result": {"message_id": 1}}
        )
        with tempfile.TemporaryDirectory() as directory:
            config = run_config(Path(directory) / "state.json")
            apt_cron.run_once(transport, config)
            transport.attachments_response["results"][0]["files"].append(NEW_PDF)
            response["results"][0]["cntTitle"] = "Titolo aggiornato"
            transport.calls.clear()
            transport.attachment_requests.clear()

            apt_cron.run_once(transport, config)
            state = apt_cron.load_state(config["state_path"])
            sent = [call for call in transport.calls if "api.telegram.org" in call["url"]]

        self.assertEqual(transport.attachment_requests, ["791962"])
        self.assertIn(NEW_PDF["downloadUrl"], state["attachments"]["791962"]["attachment_urls"])
        self.assertIn(NEW_PDF["downloadUrl"], state["sent_documents"])
        self.assertEqual(len(sent), 5)

    def test_unchanged_notice_reuses_the_cached_attachment_links(self):
        response = json.loads(FIXTURE.read_text(encoding="utf-8"))
        transport = CountingAttachmentsTransport(
            response, {"ok": True, "result": {"message_id": 1}}
        )
        with tempfile.TemporaryDirectory() as directory:
            config = run_config(Path(directory) / "state.json")
            apt_cron.run_once(transport, config)
            transport.calls.clear()
            transport.attachment_requests.clear()

            stats = apt_cron.run_once(transport, config)
            sent = [call for call in transport.calls if "api.telegram.org" in call["url"]]

        self.assertEqual(stats["published"], 0)
        self.assertEqual(transport.attachment_requests, [])
        self.assertEqual(sent, [])

    def test_a_refreshed_notice_with_the_same_links_uploads_no_duplicate(self):
        response = json.loads(FIXTURE.read_text(encoding="utf-8"))
        transport = CountingAttachmentsTransport(
            response, {"ok": True, "result": {"message_id": 1}}
        )
        with tempfile.TemporaryDirectory() as directory:
            config = run_config(Path(directory) / "state.json")
            apt_cron.run_once(transport, config)
            response["results"][0]["cntTitle"] = "Titolo aggiornato"
            apt_cron.run_once(transport, config)
            response["results"][0]["cntTitle"] = "Titolo aggiornato di nuovo"
            transport.calls.clear()
            transport.attachment_requests.clear()

            apt_cron.run_once(transport, config)
            sent = [call for call in transport.calls if "api.telegram.org" in call["url"]]

        self.assertEqual(transport.attachment_requests, ["791962"])
        self.assertEqual(len(sent), 1)
        self.assertIn("sendMessage", sent[0]["url"])


class InMemoryDocumentDeliveryTest(unittest.TestCase):
    def test_run_once_uploads_the_fetched_bytes_and_writes_no_document_file(self):
        response = json.loads(FIXTURE.read_text(encoding="utf-8"))
        transport = DynamicAttachmentsTransport(response, {"ok": True, "result": {"message_id": 1}})
        with tempfile.TemporaryDirectory() as directory:
            config = run_config(Path(directory) / "state.json")
            apt_cron.run_once(transport, config)
            response["results"][0]["cntTitle"] = "Titolo aggiornato"
            transport.calls.clear()

            stats = apt_cron.run_once(transport, config)
            written = sorted(
                str(path.relative_to(directory))
                for path in Path(directory).rglob("*")
                if path.is_file()
            )
            state_text = Path(config["state_path"]).read_text(encoding="utf-8")
            index_text = (Path(config["index_dir"]) / "index.json").read_text(encoding="utf-8")

        self.assertEqual(stats["published"], 1)
        documents = [call for call in transport.calls if "sendDocument" in call["url"]]
        self.assertEqual(len(documents), 2)
        for call in documents:
            self.assertEqual(call["content"], DOCUMENT_BYTES)
        self.assertEqual(
            written,
            ["public/index.html", "public/index.json", "public/index.md", "state.json"],
        )
        self.assertIn("https://example.test/documento-791962.pdf", state_text)
        self.assertIn("https://example.test/documento-791962.pdf", index_text)
        for text in (state_text, index_text):
            self.assertNotIn("in-memory document payload", text)

    def test_an_oversized_pdf_aborts_before_any_upload(self):
        self.assertEqual(apt_cron.DOCUMENT_MAX_BYTES, 50 * 1024 * 1024)
        response = json.loads(FIXTURE.read_text(encoding="utf-8"))
        transport = DynamicAttachmentsTransport(response, {"ok": True, "result": {"message_id": 1}})
        transport.fetch_bytes = lambda url: b"x" * 11
        with tempfile.TemporaryDirectory() as directory:
            config = run_config(Path(directory) / "state.json")
            apt_cron.run_once(transport, config)
            response["results"][0]["cntTitle"] = "Titolo aggiornato"
            transport.calls.clear()

            with mock.patch.object(apt_cron, "DOCUMENT_MAX_BYTES", 10):
                stats = apt_cron.run_once(transport, config)
            documents = [call for call in transport.calls if "sendDocument" in call["url"]]
            state = apt_cron.load_state(config["state_path"])

        self.assertEqual(stats["document_errors"], 1)
        self.assertEqual(documents, [])
        self.assertEqual(state["sent_documents"], {})


class ProductionConfigTest(unittest.TestCase):
    def test_refresh_index_and_backfill_cannot_be_combined(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                apt_cron.main(["--refresh-index", "--backfill"])

        self.assertEqual(raised.exception.code, 2)

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
        notice.update(
            number=244,
            year=2026,
            detail_url="https://example.test/albo-pretorio/dettaglio/" + "a" * 5000,
            document_url="https://example.test/documento.pdf",
            attachment_urls=["https://example.test/allegato.png"],
        )

        message = apt_cron.format_message(
            notice,
            "https://example.test/albo-pretorio/dettaglio",
        )

        self.assertLessEqual(len(message), apt_cron.TELEGRAM_TEXT_LIMIT)
        self.assertIn('href="https://example.test/albo-pretorio/dettaglio/', message)
        self.assertIn('href="https://example.test/documento.pdf">PDF ufficiale</a>', message)
        self.assertIn('href="https://example.test/allegato.png">Allegato</a>', message)
        self.assertIn("Titolo:", message)
        for tag in ("b", "u", "blockquote", "a"):
            self.assertEqual(
                message.count(f"<{tag}>") + message.count(f"<{tag} "),
                message.count(f"</{tag}>"),
                tag,
            )


class FailingDocumentTransport(SequenceTransport):
    def __init__(self, source_response, attachments_response, failing_url):
        super().__init__(
            source_response, {"ok": True, "result": {"message_id": 1}}, attachments_response
        )
        self.failing_url = failing_url
        self.failed = False

    def fetch_bytes(self, url):
        if not self.failed and url == self.failing_url:
            self.failed = True
            raise RuntimeError("PDF temporarily unavailable")
        return super().fetch_bytes(url)


class PdfRetryTest(unittest.TestCase):
    PDF_URLS = [
        "https://example.test/docs/documentoUnico.pdf",
        "https://example.test/docs/allegato-1.pdf",
        "https://example.test/docs/allegato-2.pdf",
        "https://example.test/docs/allegato-3.pdf",
    ]

    def attachments_response(self):
        return {
            "error": False,
            "results": [
                {
                    "documentoUnico": {
                        "mimeType": "application/pdf",
                        "downloadUrl": self.PDF_URLS[0],
                    },
                    "files": [
                        {"mimeType": "application/pdf", "downloadUrl": url}
                        for url in self.PDF_URLS[1:]
                    ]
                    + [
                        {
                            "mimeType": "image/png",
                            "downloadUrl": "https://example.test/docs/non-pdf.png",
                        }
                    ],
                }
            ],
        }

    def test_all_documents_follow_one_message_and_non_pdf_is_sent(self):
        source = {"results": [archive_item(799999, "2026-11-25", 250)]}
        transport = SequenceTransport(
            source,
            {"ok": True, "result": {"message_id": 1}},
            self.attachments_response(),
        )
        with tempfile.TemporaryDirectory() as directory:
            config = run_config(Path(directory) / "state.json")
            apt_cron.run_once(transport, config)
            source["results"][0]["cntTitle"] += " aggiornato"
            transport.calls.clear()

            stats = apt_cron.run_once(transport, config)
            sent = [call for call in transport.calls if "api.telegram.org" in call["url"]]
            fetched = [
                call["url"]
                for call in transport.calls
                if call["method"] == "GET" and call["url"].startswith("https://example.test/docs/")
            ]
            state = apt_cron.load_state(config["state_path"])

        self.assertEqual(stats["published"], 1)
        all_urls = self.PDF_URLS + ["https://example.test/docs/non-pdf.png"]
        self.assertEqual(len(sent), 6)
        self.assertIn("sendMessage", sent[0]["url"])
        self.assertEqual([call["url"] for call in sent[1:]], [config["document_base"]] * 5)
        self.assertEqual(fetched, all_urls)
        self.assertEqual(
            [call["filename"] for call in sent[1:]],
            [url.rsplit("/", 1)[1] for url in all_urls],
        )
        self.assertEqual(set(state["sent_documents"]), set(all_urls))

    def test_duplicate_pdf_urls_are_uploaded_once(self):
        source = {"results": [archive_item(799999, "2026-11-25", 250)]}
        duplicate = {
            "error": False,
            "results": [
                {
                    "documentoUnico": {
                        "mimeType": "application/pdf",
                        "downloadUrl": self.PDF_URLS[0],
                    },
                    "files": [
                        {"mimeType": "application/pdf", "downloadUrl": self.PDF_URLS[0]},
                        {"mimeType": "application/pdf", "downloadUrl": self.PDF_URLS[1]},
                        {"mimeType": "application/pdf", "downloadUrl": self.PDF_URLS[1]},
                    ],
                }
            ],
        }
        transport = SequenceTransport(
            source, {"ok": True, "result": {"message_id": 1}}, duplicate
        )
        with tempfile.TemporaryDirectory() as directory:
            config = run_config(Path(directory) / "state.json")
            apt_cron.run_once(transport, config)
            source["results"][0]["cntTitle"] += " aggiornato"
            transport.calls.clear()

            apt_cron.run_once(transport, config)
            sent = [call for call in transport.calls if "sendDocument" in call["url"]]

        self.assertEqual(
            [call["filename"] for call in sent], ["documentoUnico.pdf", "allegato-1.pdf"]
        )

    def test_partial_document_failure_retries_only_missing_documents(self):
        source = {"results": [archive_item(799999, "2026-11-25", 250)]}
        transport = FailingDocumentTransport(
            source, self.attachments_response(), self.PDF_URLS[1]
        )
        with tempfile.TemporaryDirectory() as directory:
            config = run_config(Path(directory) / "state.json")
            apt_cron.run_once(transport, config)
            source["results"][0]["cntTitle"] += " aggiornato"
            transport.calls.clear()

            failed_stats = apt_cron.run_once(transport, config)
            failed_calls = [call for call in transport.calls if "api.telegram.org" in call["url"]]
            failed_state = apt_cron.load_state(config["state_path"])
            transport.calls.clear()

            stats = apt_cron.run_once(transport, config)
            recovered = [call for call in transport.calls if "api.telegram.org" in call["url"]]
            state = apt_cron.load_state(config["state_path"])

        self.assertEqual(
            [call["filename"] for call in failed_calls if "sendDocument" in call["url"]],
            ["documentoUnico.pdf"],
        )
        self.assertEqual(
            len([call for call in failed_calls if "sendMessage" in call["url"]]), 1
        )
        self.assertEqual(set(failed_state["sent_documents"]), {self.PDF_URLS[0]})
        self.assertNotEqual(
            failed_state["sent_messages"]["799999"],
            failed_state["notices"]["799999"],
        )

        self.assertEqual(failed_stats["document_errors"], 1)
        self.assertEqual(stats["published"], 0)
        self.assertEqual([call for call in recovered if "sendMessage" in call["url"]], [])
        self.assertEqual(
            [call["filename"] for call in recovered if "sendDocument" in call["url"]],
            ["allegato-1.pdf", "allegato-2.pdf", "allegato-3.pdf", "non-pdf.png"],
        )
        self.assertEqual(
            set(state["sent_documents"]),
            set(self.PDF_URLS + ["https://example.test/docs/non-pdf.png"]),
        )
        self.assertEqual(state["sent_messages"]["799999"], state["notices"]["799999"])


if __name__ == "__main__":
    unittest.main()
