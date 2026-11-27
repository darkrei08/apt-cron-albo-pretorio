#!/usr/bin/env python3
"""Build a daily Markdown report from hourly report files."""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

FIELD_PATTERNS = {
    "timestamp": re.compile(r"^- Checked at: (.+?) \(Europe/Rome\)$", re.MULTILINE),
    "outcome": re.compile(r"^- Outcome: (.+)$", re.MULTILINE),
    "message": re.compile(r"^- Result: (.+)$", re.MULTILINE),
    "new": re.compile(r"^- New acts: (\d+)$", re.MULTILINE),
    "changed": re.compile(r"^- Changed acts: (\d+)$", re.MULTILINE),
    "removed": re.compile(r"^- Acts no longer published: (\d+)$", re.MULTILINE),
}


def parse_report(path):
    text = Path(path).read_text(encoding="utf-8")
    row = {"file": Path(path).name}
    for name, pattern in FIELD_PATTERNS.items():
        match = pattern.search(text)
        if match:
            row[name] = match.group(1)
    for name in ("new", "changed", "removed"):
        row[name] = int(row.get(name, 0))
    return row


def markdown(day, rows):
    total_new = sum(row["new"] for row in rows)
    total_changed = sum(row["changed"] for row in rows)
    total_removed = sum(row["removed"] for row in rows)
    lines = [
        f"# Daily publication report — {day}",
        "",
        f"Generated: {datetime.now(ZoneInfo('Europe/Rome')).replace(microsecond=0).isoformat()}",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Hourly reports | {len(rows)} |",
        f"| New acts | {total_new} |",
        f"| Changed acts | {total_changed} |",
        f"| Acts no longer published | {total_removed} |",
        "",
        "## Runs",
        "",
        "| Report | Time | Outcome | Result |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        time = row.get("timestamp", "").split("T")[-1]
        lines.append(
            f"| `{row['file']}` | {time} | {row.get('outcome', 'unknown')} | {row.get('message', '')} |"
        )
    if not rows:
        lines.append("| — | — | no_runs | No hourly report available. |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build a daily Markdown publication report")
    parser.add_argument("--date", required=True, help="Report date in YYYY-MM-DD")
    parser.add_argument("--input-dir", required=True, help="Directory containing hourly Markdown reports")
    parser.add_argument("--output", required=True, help="Markdown output path")
    args = parser.parse_args(argv)
    try:
        directory = Path(args.input_dir)
        files = sorted(directory.glob("*.md")) if directory.is_dir() else []
        rows = [parse_report(path) for path in files]
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(markdown(args.date, rows), encoding="utf-8")
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
