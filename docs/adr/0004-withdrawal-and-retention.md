# 0004 — Withdrawal and retention of messages, state and index

- Status: accepted
- Decision record: GitHub issue #11 (closed)

## Context

The repository has no withdrawal or retention mechanism. What it does have:

- **Expiry is published but unused for retention.** `cntDataFinePubblicazione` is projected into
  the notice, published in the Telegram message and the index, and fingerprinted. No code path acts
  on it for retention: no pruning, no expiry message, no deletion.
- **State grows without bound.** `state["sent_documents"]` maps every delivered PDF URL to its
  notice key (`apt_cron.py:313-315`), and `state["attachments"]` caches PDF links per notice
  (`apt_cron.py:242-259`), refreshed whenever the notice's source metadata changes so a newly added
  official PDF can be published. Neither map is pruned, and `expires` is not stored in state at
  all — state keeps fingerprints, not notice fields.
- **The index is rebuilt, and its published history lives in Git.** `run_once` regenerates
  `public/index.*` from the notices the source returned on that run (`apt_cron.py:318-319`,
  `write_index` `apt_cron.py:190-240`), and `--refresh-index` does the same without state
  (`apt_cron.py:278-281`). A notice that leaves the source page disappears from the index on the
  next refresh, but its Telegram message, its `sent_documents` entry and every previously committed
  `public/index.*` snapshot remain.
- **Message identity is thrown away.** `publish_message` and `publish_document` return
  `response["result"]` (`apt_cron.py:323-328`, `apt_cron.py:161-169`), and `run_once` discards both
  return values (`apt_cron.py:297-317`). Without storing `message_id`, a later edit or delete of a
  published message requires manual work in the Telegram client.
- **Removal is delegated to the operator.** `README.md:102` makes the operator responsible for
  answering data-rights requests, with no procedure attached.

This ADR fixes the *structure* of the policy. It does not implement deletion, and no runtime
behavior changes here.

Operator decisions are recorded below.

## Decision

1. **Withdrawal action.** Accepted: no automatic action. A withdrawn notice is not deleted from the
   channel; messages remain in the chat as the permanent record. The script has no
   `deleteMessage` call and none is added.
2. **Retention of state.** Accepted: indefinite. Fingerprints, cached PDF links and sent document URLs
   are kept for the life of the deployment and no pruning rule is added. The cached PDF links are
   replaced, not appended, when a notice changes, so retention covers the per-notice entry rather
   than its first content. Deleting the state file
   (`APT_STATE_PATH`) remains only the documented re-seed path, not a retention mechanism.
3. **Retention of published messages.** Accepted: messages stay in the channel indefinitely as the
   publishing record. Withdrawal is triggered by the source, not by age, and requires no action.
4. **Index retention.** Accepted: indefinite. The index is regenerated and published on GitHub every
   hour by `.github/workflows/update-index.yml`, which commits only changed `public/index.*`; Git
   history keeps every published state, so a notice that leaves the source page stays visible in
   earlier commits and disappears from the current files.
5. **Rights-request owner and service level.** Accepted: the repository operator answers data-rights
   requests within five working days and keeps a written record of each answer. No removal procedure
   is implemented, consistent with item 1.
6. **What must be recorded to make withdrawals auditable.** Accepted: no `message_id` is stored. The
   chat itself is the permanent record, so deletion is not part of this workflow and no state schema
   change is needed.

## Consequences

- Withdrawal is correct-by-decision, not by code: a withdrawn notice persists in the channel by
  design, and nothing detects the withdrawal because the source simply stops returning the notice.
- Because `sent_documents` never prunes, a PDF URL is sent at most once for the whole life of the
  state file (`apt_cron.py:308-310`); any future pruning rule must be justified against that
  guarantee, which is why item 2 keeps retention indefinite.
- The committed index makes the repository a publication surface whose history is not removable by a
  normal commit: dropping a notice from `public/index.*` leaves it in earlier commits (ADR 0005 item
  2). Indefinite index retention accepts that trade-off.
- Not storing `message_id` (item 6) keeps the state schema and publish path unchanged; the chat
  history is the audit trail by decision.
- Deleting `APT_STATE_PATH` remains the documented re-seed path (ADR 0001) and is *not* a retention
  mechanism: it suppresses publishing for one run and forgets sent documents.

## Evidence

- `apt_cron.py`: `NOTICE_FIELDS`, `INDEX_FIELDS`, `build_index`,
  `write_index` `:190-240`, `enrich_notices` `:242-259`, `refresh_index` `:278-281`, `run_once`
  `:284-320`, success saves `:297-317`, state rebuild `:318-319`, `publish_document` return
  `:161-169`, `publish_message` return `:323-328`.
- `tests/test_apt_cron.py`: `test_pdf_is_not_sent_again_when_notice_changes_again`,
  `test_state_round_trip_in_temporary_directory`, `test_migrates_legacy_state_without_losing_fingerprints`
  — none exercise deletion or retention.
- `README.md:98` (what state contains), `:102` (operator responsibility and no automated
  withdrawal), `:85-88` (hourly index commit).
- `.github/workflows/update-index.yml` (hourly refresh that commits `public/index.*`).
- `docs/wayfinder-execution-order.md` row 5.

## Not verified

No retention job, deletion call or rights-request procedure exists in code or tests. The source's own
withdrawal semantics (whether a withdrawn notice truly leaves the filtered page) are unverified; a
live check is required before item 1 can be relied on as an accurate archive.
