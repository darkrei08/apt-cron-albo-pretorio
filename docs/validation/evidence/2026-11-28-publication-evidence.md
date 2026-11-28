# GitHub publication evidence — 2026-11-28

Remote: `https://github.com/darkrei08/apt-cron-albo-pretorio.git`

## Published state

- First pushed head: `f8cd8bdefd48e6c07c2fae6d8e28fb5b65b63305`.
- Remote HEAD checked with `gh api repos/darkrei08/apt-cron-albo-pretorio/commits/main`: the same SHA.
- Push command: `git push origin main`; exit `0`; output `4373dbe..f8cd8bd  main -> main`.
- No reset, no force push and no commit deletion.

## Exact-commit CI

`gh run list --repo darkrei08/apt-cron-albo-pretorio --limit 12` recorded both checks on `f8cd8bde`:

| Workflow | Run | Conclusion |
|---|---:|---|
| CI | `46147040330` | `success` |
| Quality | `46147040343` | `success` |

## Publication verification

- Secret rotation verification: `Publish acts and reports` run `46146401728`, `success`, all 12 steps PASS, report `no_new_acts_to_publish`.
- Local evidence: 142 tests PASS, compile PASS, isolated `--dry-run` PASS with `published: 0`, `git diff --check` PASS.
- No Telegram token value appears in any repository file.

## Not verified

Live Telegram delivery, protected host filesystem metadata, observed manual production run, 24-hour observation and rollback rehearsal remain NOT RUN. The Wayfinder gate stays `HOLD`; this record only proves that the repository work and evidence are published.
