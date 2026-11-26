# 0004 — Withdrawal and retention of messages, state and index

- Status: proposed (operator input required)
- Decision record: GitHub issue #11 (open)

## Context

The repository has no withdrawal or retention mechanism. What it does have:

- **Expiry is captured but unused for retention.** `NOTICE_FIELDS["expires"]` maps
  `cntDataFinePubblicazione` (`apt_cron.py:15-25`); the value is copied into the index row
  (`INDEX_FIELDS`, `apt_cron.py:172-185`) and appears nowhere else. No code path acts on it: no
  pruning, no expiry message, no deletion.
- **State grows without bound.** `state["sent_documents"]` maps every delivered PDF URL to its
  notice key (`apt_cron.py:308-310`), and `state["attachments"]` caches PDF links per notice
  (`apt_cron.py:247-263`). Neither map is pruned, and `expires` is not stored in state at all —
  state keeps fingerprints, not notice fields.
- **The index is rebuilt, not retained.** `run_once` regenerates `public/index.*` from the notices
  the source returned on that run (`apt_cron.py:313-314`, `write_index` `apt_cron.py:192-244`). A
  notice that leaves the source page silently disappears from the index on the next run, but its
  Telegram message and its `sent_documents` entry remain.
- **Message identity is thrown away.** `publish_message` and `publish_document` return
  `response["result"]` (`apt_cron.py:318-323`, `apt_cron.py:161-169`), and `run_once` discards both
  return values (`apt_cron.py:292-307`). Without storing `message_id`, a later edit or delete of a
  published message requires manual work in the Telegram client.
- **Removal is delegated to the operator.** `README.md:83` makes the operator responsible for
  "deciding how to remove published messages if a source notice is withdrawn or a data-rights
  request arrives", with no procedure attached.

This ADR fixes the *structure* of the policy. It does not implement deletion, and no runtime
behavior changes here.

Decisions the operator must make are marked `[INSERT DECISION]` with a recommendation.

## Decision

1. **Withdrawal action.** `[INSERT DECISION]` — *Recommendation: a manual, documented procedure —
   delete the channel message and remove the notice from the regenerated index by re-running after
   the source stops returning it — performed by the named owner, with no automatic deletion in
   code.* An automated delete would need `message_id` in state and a Telegram `deleteMessage` call,
   which is new runtime behavior outside this ADR's scope.
2. **Retention of state.** `[INSERT DECISION]` — *Recommendation: keep fingerprints and
   `sent_documents` while production runs, and prune `attachments` entries whose notice `id` is
   absent from the source for a stated number of consecutive runs; the exact window is
   `[INSERT DECISION]`. Recommendation: 90 days.* Pruning needs `expires` or a first-seen date to be
   recorded in state first, which is an implementation change and is explicitly **not** made here.
3. **Retention of published messages.** `[INSERT DECISION]` — *Recommendation: messages stay in the
   channel indefinitely as publishing record; withdrawal is triggered by the source, not by age.*
   This keeps the channel an accurate archive of what the register published.
4. **Index retention.** `[INSERT DECISION]` — *Recommendation: the generated index reflects only the
   current source page and is overwritten on each run (today's behavior); committed copies are the
   operator's responsibility, so no history is kept in Git beyond what the operator commits.*
5. **Rights-request owner and service level.** `[INSERT DECISION]` — *Recommendation: name one owner
   (with a backup) for data-rights and withdrawal requests, with a stated response window —
   recommendation 5 working days — and a written record of each completed removal.*
6. **What must be recorded to make withdrawals auditable.** `[INSERT DECISION]` — *Recommendation:
   record `message_id` for message and document sends, because it is currently returned and dropped
   and is the only handle for later edits or deletions.*

## Consequences

- Withdrawal is correct-by-operator today, not correct-by-code: a withdrawn notice persists in the
  channel until someone acts, and nothing detects the withdrawal because the source simply stops
  returning the notice.
- Because `sent_documents` never prunes, a PDF URL is sent at most once for the whole life of the
  state file (`apt_cron.py:299-300`); pruning it would re-send documents for notices that reappear,
  so any pruning rule must be justified against that guarantee.
- Storing `message_id` (item 6) would change both the state schema and the publish path; it needs its
  own ticket and a state migration, not an edit to this ADR.
- Deleting `APT_STATE_PATH` remains the documented re-seed path (ADR 0001) and is *not* a retention
  mechanism: it suppresses publishing for one run and forgets sent documents.

## Evidence

- `apt_cron.py`: `NOTICE_FIELDS` `:15-25`, `INDEX_FIELDS` `:172-185`, `build_index` `:188-190`,
  `write_index` `:192-244`, `enrich_notices` `:247-263`, `run_once` `:266-316`, success saves
  `:291-310`, state rebuild `:313-314`, `publish_document` return `:161-169`, `publish_message`
  return `:318-323`.
- `tests/test_apt_cron.py`: `test_pdf_is_not_sent_again_when_notice_changes_again`,
  `test_state_round_trip_in_temporary_directory`, `test_migrates_legacy_state_without_losing_fingerprints`
  — none exercise deletion or retention.
- `README.md:83` (operator responsibility for removal), `:78` (what state contains).
- `docs/wayfinder-execution-order.md` row 5.

## Not verified

No retention job, deletion call or rights-request procedure exists in code or tests. The source's own
withdrawal semantics (whether a withdrawn notice truly leaves the filtered page) are unverified; a
live check is required before item 1 can be relied on.
