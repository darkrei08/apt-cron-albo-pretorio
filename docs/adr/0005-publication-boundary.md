# 0005 — Publication boundary: what may be published, retained and removed

- Status: accepted
- Decision record: GitHub issue #6 (open)

## Context

The repository enforces its publication boundary with two explicit allowlists and one generation
path:

- **Source allowlist.** `NOTICE_FIELDS` (`apt_cron.py:21-63`) maps 41 of the 53 source keys an act
  carries: nine under stable output names (`id`, `title` = `cntTitle`, `category` =
  `cntNaturaAttoLabel`, `sector` = `cntSettoreProponenteLabel`, `published` =
  `cntDataInizioPubblicazione`, `expires` = `cntDataFinePubblicazione`, `year` =
  `cntAnnoNumeroPap`, `number` = `cntNumeroPap`, `status`) and the other 32 under their register key.
  `parse_source_response` (`apt_cron.py:110-114`) projects each source item through that map, so a
  key the API returns but that is not listed is dropped before anything else in the program sees it.
- **Excluded keys.** The 12 source keys that stay out are the internal account, login, audit and
  responsible-person columns: `cntAutore`, `cntAutoreAnnullamento`,
  `cntAutoreAnnullamentoLogin`, `cntAutoreLogin`, `cntAutoreRigetto`, `cntAutoreRigettoLogin`,
  `cntResponsabileProcedimento`, `cntResponsabileProcedimentoLogin`,
  `cntResponsabilePubblicazione`, `cntResponsabilePubblicazioneLogin`, `ultimaAnnotazioneModifica`
  and `ultimaAnnotazioneRipubblicazione`. None of them is projected, fingerprinted or rendered.
- **Index allowlist.** `INDEX_FIELDS` (`apt_cron.py:263`) is built from `NOTICE_FIELDS`, not written
  a second time: it is `tuple(NOTICE_FIELDS)` plus the derived `detail_url`, `document_url` and
  `attachment_urls`. `build_index` (`apt_cron.py:278-279`) projects through it, and `write_index`
  (`apt_cron.py:282-331`) renders every non-empty field to `index.json`, `index.md` and
  `index.html` using the labels in `FIELD_LABELS` (`apt_cron.py:65-107`), HTML-escaping every value.
- **Title and sector are published again.** Both are formatted into the Telegram message and the
  index, and both are fingerprinted, so a change to either produces an "Atto aggiornato" message.
  This supersedes the earlier decision to keep them internal.
- **Source payload carries more than the allowlist.** The test fixture
  `tests/fixtures/source_response.json` includes `cntResponsabileProcedimento` alongside the allowed
  fields; it is not in `NOTICE_FIELDS`, so it never reaches state, Telegram or the index. The fixture
  is synthetic (`"NOT IN OUTPUT"`, `"ALSO NOT IN OUTPUT"`).
- **Two publication surfaces exist, both described as such.** Telegram is the intended surface. The
  generated index is written to `APT_INDEX_DIR` (`public/` by default, `apt_cron.py:580-581`), is not
  ignored by `.gitignore`, and is committed to this repository every hour by
  `.github/workflows/update-index.yml` with the repository `GITHUB_TOKEN`. A committed
  `public/index.*` is therefore public a second time, through the repository and any hosting of it.

Operator decisions are recorded below.

## Decision

1. **Publication surfaces.** Accepted: exactly two — the Telegram channel and the generated index
   published on GitHub and kept updated hourly. The index counts as publication, so the same field
   boundary applies to both.
2. **Whether the index is committed.** Accepted: yes. `.github/workflows/update-index.yml` commits
   changed `public/index.*` every hour from the repository's own default-hosted source, using the
   repository `GITHUB_TOKEN` and no Telegram credentials. Removal from Git history is not covered by
   any current procedure; that is accepted, and the index is retained indefinitely (ADR 0004 item 4).
3. **Publish every publicly obtainable field.** Accepted: the published maximum is the 41 included
   source keys plus the derived `detail_url`, `document_url` and `attachment_urls`. The included keys
   are the nine aliased ones (`id`, `cntTitle`, `cntNaturaAttoLabel`, `cntSettoreProponenteLabel`,
   `cntDataInizioPubblicazione`, `cntDataFinePubblicazione`, `cntAnnoNumeroPap`, `cntNumeroPap`,
   `status`) and `otypeId`, `rootId`, `rootOtypeid`, `cntAutoritaMittente`, `cntAnnoNumeroRpap`,
   `cntDataAnnullamento`, `cntDataAnnullamentoTime`, `cntDataDocumentoOrigine`, `cntDataNumeroPap`,
   `cntDataNumeroPapTime`, `cntDataNumeroRpap`, `cntDataNumeroRpapTime`, `cntDataRigetto`,
   `cntDataRigettoTime`, `cntDate`, `cntDocumentoOrigine`, `cntDurataPubblicazione`, `cntExternalId`,
   `cntExternalOggetto`, `cntExternalSource`, `cntExternalStatus`, `cntNaturaAtto`,
   `cntNoteAnnullamento`, `cntNoteRigetto`, `cntNumeri`, `cntNumeroDocumentoOrigine`, `cntNumeroGara`,
   `cntNumeroRpap`, `cntParentObjectId`, `cntParentOtypeId`, `cntProponente`, `cntSettoreProponente`.
   The 12 excluded keys are listed in Context. `Titolo` and `Settore` are published, so the Telegram
   message, the document flow and the index carry them again. Adding one of the excluded keys, or
   dropping an included one, requires a new ADR.
4. **Proof required for the PII boundary.** Accepted after a live source inspection: account, login,
   responsible-person and last-annotation fields are excluded from the allowlist; every other field
   returned for a public act is published, including free-text `Titolo` and `Settore`. A live title
   sample names economic operators ("in favore dell'operatore economico ..."); that text is register
   content and is now published deliberately. No redaction is applied.
5. **Review owner for the index.** Accepted: no per-index human review. The hourly commit path is
   unattended on purpose, so the field allowlist and the tests that assert the excluded keys never
   appear in a published output are the control; the maintainer named in ADR 0003 owns it.

## Consequences

- The allowlists are the privacy mechanism, and they are enforced in one place each: `NOTICE_FIELDS`
  is the projection and fingerprint source, and `INDEX_FIELDS` is derived from it. `format_message`
  renders the identity block plus every other non-empty published field; `document_caption` uses the
  act number and year only. Widening or narrowing any of them is a decision, not an implementation
  detail — this matches ADR 0001 §3.
- **One-time reseed on deploy.** Fingerprints cover every projected field, so the allowlist change
  changes every existing fingerprint. Deleting or moving `APT_STATE_PATH` before the first run after
  the deploy makes that run seed state silently; without it, the first run reports every current
  notice as "Atto aggiornato" and republishes the messages. Either outcome is expected once and is
  not a defect. Documented for operators in `README.md`.
- Because the index is a publication surface (item 1) published unattended (items 2 and 5),
  `write_index` escaping and the field projection are publish-boundary code: any future edit to them
  needs the same review as a field change, and the tests assert the absence of the excluded keys
  through the public run path.
- The message is longer than before: an act with many filled fields renders one line per field, still
  bounded at 4096 characters by truncating the widest lines (`_bounded`, `apt_cron.py:437-448`).
  A pathological value is shortened, not dropped unbounded.
- A notice removed from the source leaves the current `public/index.*` on the next hourly refresh but
  stays in earlier Git commits. That history is accepted under ADR 0004 item 4 and is not removable
  by a normal commit.
- Item 4 is accepted: the field map was checked against a live source sample and the operator
  accepted the register text in free-text fields; internal account, login, audit and responsible-person
  fields stay excluded.

## Evidence

- `apt_cron.py`: `NOTICE_FIELDS` `:21-63`, `FIELD_LABELS` `:65-107`, `parse_source_response`
  `:110-114`, `fingerprint` `:146-148`, `INDEX_FIELDS` `:263`, `_field_rows` `:269-275`,
  `build_index` `:278-279`, `write_index` `:282-331`, `refresh_index` `:370-373`, `document_caption`
  `:426-430`, `MESSAGE_IDENTITY_FIELDS` `:434`, `_bounded` `:437-448`, `format_message`
  `:451-469`, `--index-dir` default `:580-581`.
- `.github/workflows/update-index.yml`: hourly and manual dispatch, `TZ: Europe/Rome`, commits only
  `public/index.json`, `public/index.md` and `public/index.html`.
- `tests/test_apt_cron.py`: `INCLUDED_SOURCE_FIELDS` and `EXCLUDED_SOURCE_FIELDS` pin both sets,
  `test_projects_every_documented_public_source_field`,
  `test_formats_plain_text_with_searchable_fields_and_official_link`,
  `test_includes_every_public_field_and_never_an_internal_one`,
  `test_published_fields_are_the_notice_fields_plus_derived_links`,
  `test_build_index_publishes_every_public_field`, `test_write_index_creates_json_markdown_and_html`,
  `test_write_index_renders_every_non_empty_public_field`,
  `test_document_caption_carries_no_public_or_internal_text`,
  `test_writes_public_index_without_state_or_telegram`.
- `tests/fixtures/source_response.json`: allowed fields plus `cntResponsabileProcedimento`, which is
  dropped by the projection; values are synthetic.
- `README.md:22` (two publication surfaces and the published set), `:100` (what is saved and
  published), `:104` (operator duties, the reseed note and the new-decision clause).
- `.gitignore`: `state/` and `cron.log` are ignored; `public/` is not.
- `docs/wayfinder-execution-order.md` row 6 (blocked on row 5).

## Not verified

A live source inspection and a live `--refresh-index` run were performed (exit code `0`, 14 notices,
44 published keys per notice, no state file and no Telegram credential). The live run confirmed that
`Titolo` and `Settore` are back in the index and that no excluded key appears in the published index.
There is no automated PII classifier or redaction; free-text register values are published by the
operator's explicit decision and must be reviewed only if policy changes.
