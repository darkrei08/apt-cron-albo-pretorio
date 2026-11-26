# 0005 — Publication boundary: what may be published, retained and removed

- Status: proposed (operator input required)
- Decision record: GitHub issue #6 (open)

## Context

The repository enforces its publication boundary with two explicit allowlists and one generation
path:

- **Source allowlist.** `NOTICE_FIELDS` (`apt_cron.py:15-25`) maps exactly nine source fields:
  `id`, `title`, `category` (`cntNaturaAttoLabel`), `sector` (`cntSettoreProponenteLabel`),
  `published` (`cntDataInizioPubblicazione`), `expires` (`cntDataFinePubblicazione`), `year`,
  `number` and `status`. `parse_source_response` (`apt_cron.py:28-32`) projects each source item
  through that map, so any field the API returns but that is not listed is dropped before anything
  else in the program sees it.
- **Index allowlist.** `INDEX_FIELDS` (`apt_cron.py:172-185`) adds only `detail_url`,
  `document_url` and `attachment_urls` to the nine fields, and `build_index` (`apt_cron.py:188-190`)
  projects through it. `write_index` (`apt_cron.py:192-244`) renders those rows to
  `index.json`, `index.md` and `index.html`, HTML-escaping title, dates, number and URLs.
- **Source payload carries more than the allowlist.** The test fixture
  `tests/fixtures/source_response.json` includes `cntResponsabileProcedimento` alongside the allowed
  fields; it is not in `NOTICE_FIELDS`, so it never reaches state, Telegram or the index. The fixture
  is synthetic (`"NOT IN OUTPUT"`, `"ALSO NOT IN OUTPUT"`), so it proves the projection, not what the
  real payload contains.
- **Two publication surfaces exist, only one is described as such.** Telegram is the intended
  surface. The generated index is written to `APT_INDEX_DIR` (`public/` by default,
  `apt_cron.py:405`), is not ignored by `.gitignore`, and `README.md:78` says the files "can be
  reviewed and committed by the operator", with `README.md:83` making that review the operator's
  duty. A committed `public/index.*` is therefore public a second time, through the repository and
  any hosting of it.

Decisions the operator must make are marked `[INSERT DECISION]` with a recommendation.

## Decision

1. **Publication surfaces.** `[INSERT DECISION]` — *Recommendation: exactly two — the Telegram
   channel and the generated index — and the index counts as publication, so the same allowlist and
   review rule applies to both.* Naming the surfaces is what makes "published" reviewable; today the
   README treats the index as an artifact and the issue treats it as publication.
2. **Whether the index is committed.** `[INSERT DECISION]` — *Recommendation: do not commit
   `public/index.*`; publish it from the run host, because a commit makes removal from the
   repository history a separate retention problem that no current procedure covers.* If it is
   committed, record that decision and revisit ADR 0004 item 4.
3. **Field boundary is frozen here.** `[INSERT DECISION]` — *Recommendation: keep the nine source
   fields plus the three derived URL fields as the maximum, and require a new ADR to add any field.*
   Adding `cntResponsabileProcedimento`, RUP names, responsible persons or non-public groups is
   explicitly out of scope, consistent with `README.md:78` and `:83`.
4. **Proof required for the PII boundary.** `[INSERT DECISION]` — *Recommendation: one recorded
   inspection of a real source response (not the fixture) confirming that only allowlisted fields
   are consumed, performed by a named reviewer and recorded in `docs/validation/`.* The code
   projection is verified by tests; the claim that the real payload holds no other personal data we
   retain is not.
5. **Review owner for the index.** `[INSERT DECISION]` — *Recommendation: the same named owner as
   the withdrawal procedure in ADR 0004, reviewing each regenerated index before it is published,
   with no unattended commit path.*

## Consequences

- The allowlists are the privacy mechanism, and they are enforced in one place each. Widening either
  one is a decision, not an implementation detail — this matches ADR 0001 §3.
- Until item 4 is answered, the statement "no personal names, RUP names or responsible persons are
  written" (`README.md:78`) rests on the field map and a synthetic fixture, not on the real payload.
- If the index is treated as a publication surface (item 1) then `write_index`'s escaping and field
  projection become publish-boundary code, so any future edit to it needs the same review as a field
  change.
- Retention and removal for both surfaces remain governed by ADR 0004 and are not resolved here.

## Evidence

- `apt_cron.py`: `NOTICE_FIELDS` `:15-25`, `parse_source_response` `:28-32`, `INDEX_FIELDS`
  `:172-185`, `build_index` `:188-190`, `write_index` `:192-244`, `--index-dir` default `:403-405`.
- `tests/test_apt_cron.py`: `test_extracts_only_allowed_notice_fields`,
  `test_build_index_keeps_only_public_fields`, `test_write_index_creates_json_markdown_and_html`.
- `tests/fixtures/source_response.json`: allowed fields plus `cntResponsabileProcedimento`, which is
  dropped by the projection; values are synthetic.
- `README.md:78` (what is written, index reviewable and committable), `:83` (operator duties and the
  "new Wayfinder decision" clause).
- `.gitignore`: `state/` and `cron.log` are ignored; `public/` is not.
- `docs/wayfinder-execution-order.md` row 6 (blocked on row 5).

## Not verified

No real source response was inspected in this task, so the personal-data content of the live payload
is unverified; the fixture's `cntResponsabileProcedimento` value is a placeholder, not a sample of
real data. It is also unverified whether `public/index.*` has ever been committed.
