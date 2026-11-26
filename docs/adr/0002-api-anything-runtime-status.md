# 0002 — api-anything and fast-anything are not runtime dependencies

- Status: accepted
- Decision record: GitHub issue #12 (open)

## Context

`api-anything` was used during planning to inspect the APT site's own traffic and identify the
source request that the crawler would need. That work is finished and left nothing behind that the
job calls: the acquisition contract is now written in ADR 0001 and implemented in `apt_cron.py`.

`fast-anything` appears in the Wayfinder map as a possible future performance aid. It has not been
adopted, installed or wired to anything.

Two sources still read as if these tools were dependencies: the map issue's Notes (issue #1) keeps a
directive to use `api-anything`, which is superseded by this decision, and the planning narrative is
easy to mistake for a runtime requirement.

## Decision

- **Neither tool is a runtime dependency.** `apt_cron.py` invokes no external process, requires no
  Node runtime and imports nothing outside the Python standard library.
- **`api-anything` was a planning aid only.** It served to discover the source request during
  planning. Its role ended there; no ticket may reintroduce it as a runtime or build step without a
  new decision.
- **`fast-anything` is a future aid only.** It is recorded as a possible performance aid for later
  work, is not adopted, and is not required by any current task.
- **The Python standard library is the runtime authority.** Where this ADR, the map's Notes or any
  narrative disagree with the code, `apt_cron.py` on the standard library is authoritative, and the
  disagreement is resolved by editing the narrative — never by adding a tool to the runtime path.

## Consequences

- A reader cannot make a fresh checkout fail by not having these tools: `python3 apt_cron.py`
  runs with the standard library alone.
- The superseded `api-anything` directive in the map's Notes (issue #1) is stale; anyone acting on
  it should cite this ADR instead. Correcting the map is a tracker edit, outside this ADR.
- Adopting `fast-anything` later needs its own decision with a measured problem it solves.

## Evidence

- `README.md`, "How it works": states the planning use of `api-anything`, that the runtime script
  does not call it or require Node, and that `fast-anything` is a future aid rather than an
  extraction dependency.
- `README.md`, "Requirements": Python 3.11 or newer, no third-party Python package.
- `apt_cron.py`: imports are standard library only (`argparse`, `hashlib`, `html`, `json`, `os`,
  `re`, `sys`, `tempfile`, `unicodedata`, `datetime`, `pathlib`, `urllib`); HTTP goes through
  `urllib.request` in `UrllibTransport`.

## Not verified

The `api-anything` and `fast-anything` repositories named in `README.md` were not inspected for this
ADR; their capabilities are taken from the planning narrative, and neither is exercised by the test
suite.
