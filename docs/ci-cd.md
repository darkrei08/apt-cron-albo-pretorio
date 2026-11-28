# GitHub CI/CD

This repository has no npm package, no PyPI package and no container registry publication. The hourly GitHub publication workflow uses two protected Telegram repository secrets with legacy `APT_TEST_*` names, classified as production Destination-channel credentials by [ADR 0014](adr/0014-production-credential-override-and-destination-channel.md); the operator-managed host cron uses protected production-profile credentials. Other workflows do not use repository secrets. No npm, PyPI or container registry credential is used.

## Workflows

| Workflow | Trigger | Effect |
| --- | --- | --- |
| [Quality](../.github/workflows/quality.yml) | pushes to `main`, pull requests, manual dispatch, reusable call | Compiles sources and tests, runs the full suite, reads `VERSION` and reports the release gate. |
| [Check and release](../.github/workflows/release.yml) | pushes to `main`, tags `v*`, manual dispatch with an existing tag | Calls Quality, validates version and gate, verifies the tag commit, then creates or reuses a GitHub Release. |
| [Publish public index](../.github/workflows/pages.yml) | changes to `public/index.*` on `main`, manual dispatch | Deploys `public/` to GitHub Pages with `GITHUB_TOKEN` permissions only. |
| [Publish acts and reports](../.github/workflows/update-index.yml) | hourly schedule, manual dispatch with optional dry run | Publishes new or changed acts, regenerates the index, writes hourly and daily Markdown reports, then commits generated files. |

## Version contract

Version source: root `VERSION`.

- The file must contain `X.Y.Z` or `X.Y.Z-suffix`.
- Tags must be exactly `vX.Y.Z`.
- `docs/validation/release-gate.json` must carry the same version, `go: true`, and all five parts at `PASS`.
- A placeholder such as `[INSERT VERSIONE]` blocks release.

## Gate-safe release

Quality reports the current gate and exits `0`. The release job applies the same rules as a hard check and fails when the version or gate is not ready.

Current recorded state:

- Version: `[INSERT VERSIONE]`
- Gate: `HOLD`, `go: false`
- Parts: 1 and 2 `PASS`; 3, 4 and 5 `BLOCKED`
- No tag or GitHub Release is created by the current workflow run

## Publication steps for the operator

1. Keep PR #36 open and mergeable; do not merge it while the gate is `HOLD`.
2. Choose a version and replace `[INSERT VERSIONE]` in `VERSION` and `docs/validation/release-gate.json`.
3. Record evidenced GO for ADR 0007 parts 3-5 and set `go: true` and the five parts to `PASS` in the gate JSON only after the evidence exists.
4. Merge the release commit to `main` and wait for Quality to pass.
5. Push tag `vX.Y.Z` from that exact commit, or dispatch Check and release with the existing tag.
6. The workflow creates the GitHub Release if it does not exist. It never publishes to npm, PyPI or any other registry.
7. GitHub Pages deploys `public/index.html` when `public/index.*` changes on `main`.

## Not verified

- Real Telegram alert delivery.
- Windows and macOS.
- Manual count of 748 chat messages; the archive dry run counted 748 source notices and sent nothing, so no chat-message count was verified.
