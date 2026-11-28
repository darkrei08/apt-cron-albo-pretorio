# 0014 — Production credential override and Destination channel

- Status: accepted
- Supersedes: [ADR 0003](0003-production-secret-storage-and-schedule.md) and [ADR 0006](0006-notification-format-and-channel.md) for GitHub Actions credential names and channel classification; [ADR 0007](0007-release-gate.md) for credential names and retired Validation-channel wording
- Decision record: [Select the production host, public index destination and operational owner](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/26) and [Decide the production credential override and channel reclassification](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/37)

## Context

The operator selected `herdr` as the production host, GitHub Pages as the public index destination and
`darkrei08` as the sole operational owner. Two schedulers are intended: GitHub Actions and the host
cron; their exact offsets belong to the separate shared-state decision. The operator explicitly chose to reuse
`APT_TEST_TELEGRAM_BOT_TOKEN` and `APT_TEST_TELEGRAM_CHAT_ID` as the credentials used by GitHub
Actions, and to treat that chat as the production Destination channel. The former Validation channel
is retired. ADR 0003 and ADR 0007 still describe separated production credential names, and the
repository documentation still described the reused values as test-only, so technical verification
returned FAIL until this decision was recorded.

## Decision

1. **Destination channel.** The Telegram chat addressed by `APT_TEST_TELEGRAM_CHAT_ID` in GitHub
   Actions is the Destination channel for Public notices. The separate Validation channel is retired.
   The historical private-channel checklist remains validation evidence, not a second permanent
   publication surface.
2. **Legacy credential names.** `APT_TEST_TELEGRAM_BOT_TOKEN` and `APT_TEST_TELEGRAM_CHAT_ID` keep
   their names for compatibility with the workflow and the existing profile logic. When GitHub
   Actions uses them, they are production-classified credentials. They never fall back to
   `TELEGRAM_BOT_TOKEN` or `TELEGRAM_CHAT_ID`, and the host cron keeps `APT_TELEGRAM_PROFILE=production`
   with the ADR 0003 protected file.
3. **Rotation.** The token previously shared in conversation must be rotated before GO. Credential
   values remain out of the repository, issues, logs and shell commands. This decision records no
   secret value.
4. **Two schedulers.** GitHub Actions and the host cron publish to the same Destination channel.
   This ADR does not define the shared-state protocol; that remains the scope of
   [Define the shared-state protocol for the two production schedulers](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/38).
   Duplicate publication remains a release blocker until that protocol is decided.
5. **Unchanged.** `apt_cron.py`, the CLI contract, the published field set, captions, index files,
   document handling and exit codes are unchanged. This is a documentation and classification
   decision only; it does not authorize publication, push, tag or release.

## Evidence

- Operator decision: issue 26 resolution comment on GitHub.
- Security findings routed to issue 37 and its verification comment on GitHub.
- `README.md`, `GLOSSARY.md`, `docs/ci-cd.md`, ADR 0003, ADR 0006 and ADR 0007 are reconciled with
  this decision. No credential value is stored in this record.

## Consequences

- A reader no longer sees test credentials described as reusable or production credentials described
  as a separate channel that does not exist.
- The release gate remains `HOLD`. Rotation, host evidence and the shared-state protocol are still
  required before GO.
- Rollback is documentation-only: revert this ADR and the reconciled documentation if the operator
  reverses the credential classification.
