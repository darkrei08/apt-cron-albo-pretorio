# CLI contract

The Python entrypoints use one deterministic CLI contract. `apt_cron.py` is the machine-readable command: automation parses its JSON stdout and exit status instead of scraping prose. The report builders intentionally emit Markdown.

## Output

- `apt_cron.py` success writes exactly one JSON object to stdout.
- Runtime failure writes `error: <redacted message>` to stderr.
- Credential values, chat identifiers and document bytes are never written to stdout or stderr.
- Exit status is stable across entrypoints.
- Report builders write Markdown to stdout or a file by design; they do not emit JSON.

| Code | Meaning |
| ---: | --- |
| `0` | Command completed. |
| `1` | Runtime failure; stderr holds the redacted error. |
| `2` | Invalid arguments, unknown Telegram profile or invalid `APT_PAGE_SIZE`. |

## Entrypoints

| Command | Success JSON |
| --- | --- |
| `python3 apt_cron.py --dry-run` | `{"notices": N, "published": P, "dry_run": true}` plus optional error counts |
| `python3 apt_cron.py --refresh-index` | `{"notices": N}` |
| `python3 apt_cron.py --backfill --dry-run` | `{"notices": N, "published": P, "dry_run": true}` |
| `python3 apt_cron.py --backfill` | `{"notices": N, "published": P, "dry_run": false}` plus optional error counts |
| `python3 apt_cron.py` | `{"notices": N, "published": P, "dry_run": false}` plus optional error counts |
| `python3 hourly_report.py --stats FILE --stdout` | Markdown on stdout by design |
| `python3 daily_report.py --date D --input-dir DIR --output FILE` | Markdown file by design |

`apt_cron.py` remains the publisher. `hourly_report.py` and `daily_report.py` are report builders and do not contact Telegram or the Source register.

## Optional count fields

`attachment_errors` and `document_errors` appear only when non-zero. Consumers must treat absent fields as zero.

## Version and tooling boundary

No CLI-Anything wrapper is required. The repository is already a CLI with stable flags, JSON output and exit codes. `api-anything` was a planning aid that discovered the Source register request; `fast-anything` has no adopted runtime role. ADR 0002 records this boundary and ADR 0013 records the later tooling decision.

The machine-readable registry is [`docs/validation/cli-contract.json`](validation/cli-contract.json). It records the entry points, expected stdout kind, required success keys, optional count fields and exit-code meanings. It is documentation and test evidence, not a runtime dependency.

## Verification

```sh
python3 -m unittest tests.test_cli_contract
python3 -m py_compile apt_cron.py hourly_report.py daily_report.py publication_state.py
```
