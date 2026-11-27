# 0011 — Publish the procedural responsible person

- Status: accepted
- Supersedes ADR 0005 for `cntResponsabileProcedimento` only

ADR 0005 excluded every responsible-person field because they were treated as internal. The operator
now requires the official `Responsabile` shown in the public register description, and the live
source returns `cntResponsabileProcedimento` for public acts. Publishing that one field makes the
Telegram description match the register without inventing a value.

The decision is to publish `cntResponsabileProcedimento` as `Responsabile` in the Telegram HTML
message after `Scade il`. It is also included in the public index because both surfaces share the
same allowlist. All other responsible-person, login, audit and annotation fields remain excluded.

This changes the fingerprint field set. Existing state must be migrated before the next run,
otherwise unchanged acts would be treated as updates and published again.
