#!/usr/bin/env python3
"""Build a human-readable report from two generated notice indexes."""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def _load_index(path):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = payload.get("notices")
    if not isinstance(rows, list):
        raise RuntimeError("index notices must be a list")
    return rows


def _key(row):
    if not isinstance(row, dict):
        raise RuntimeError("index row must be an object")
    if row.get("id") not in (None, ""):
        return str(row["id"])
    for field in ("detail_url", "document_url", "attachment_urls"):
        value = row.get(field)
        if isinstance(value, list):
            value = value[0] if value else None
        if value:
            return re.sub(r"[^0-9A-Za-z]+", "-", str(value)).strip("-")
    raise RuntimeError("index row has no stable identifier")


def _canonical(row):
    return json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def build_report(before, after, timestamp=None):
    before_rows = {_key(row): row for row in before}
    after_rows = {_key(row): row for row in after}
    keys = set(before_rows) & set(after_rows)
    new = sorted(set(after_rows) - set(before_rows))
    removed = sorted(set(before_rows) - set(after_rows))
    changed = sorted(key for key in keys if _canonical(before_rows[key]) != _canonical(after_rows[key]))
    unchanged = sorted(key for key in keys if key not in changed)

    if new:
        outcome = "new_acts"
        message = f"New acts to download: {len(new)}"
    elif changed:
        outcome = "changed_acts"
        message = f"No new acts. Changed acts: {len(changed)}"
    elif removed:
        outcome = "removed_acts"
        message = f"No new acts. Acts no longer published: {len(removed)}"
    else:
        outcome = "no_changes"
        message = "No new acts to download and no changes."

    if timestamp is None:
        timestamp = datetime.now(ZoneInfo("Europe/Rome")).replace(microsecond=0).isoformat()
    return {
        "timestamp": timestamp,
        "timezone": "Europe/Rome",
        "outcome": outcome,
        "message": message,
        "counts": {
            "before": len(before_rows),
            "after": len(after_rows),
            "new": len(new),
            "changed": len(changed),
            "removed": len(removed),
            "unchanged": len(unchanged),
        },
        "ids": {
            "new": new,
            "changed": changed,
            "removed": removed,
        },
    }


def build_stats_report(stats, timestamp=None):
    published = int(stats.get("published", 0))
    notices = int(stats.get("notices", 0))
    errors = int(stats.get("attachment_errors", 0)) + int(stats.get("document_errors", 0))
    if errors:
        outcome = "errors"
        message = f"No publication confirmed; {errors} notice(s) had errors."
    elif published:
        outcome = "acts_to_publish"
        message = f"Acts to publish: {published}"
    else:
        outcome = "no_new_acts_to_publish"
        message = "No new or changed acts to publish."
    if timestamp is None:
        timestamp = datetime.now(ZoneInfo("Europe/Rome")).replace(microsecond=0).isoformat()
    return {
        "timestamp": timestamp,
        "timezone": "Europe/Rome",
        "outcome": outcome,
        "message": message,
        "counts": {
            "notices": notices,
            "published": published,
            "errors": errors,
            "dry_run": bool(stats.get("dry_run", False)),
        },
    }


def build_run_report(counts, timestamp=None):
    new = int(counts.get("new", 0))
    changed = int(counts.get("changed", 0))
    removed = int(counts.get("removed", 0))
    notices = int(counts.get("notices", 0))
    seeded = bool(counts.get("seeded", False))
    errors = int(counts.get("errors", 0))
    if seeded:
        outcome = "seeded"
        message = f"First run seeded {notices} acts; no publication."
    elif errors:
        outcome = "fetch_errors"
        message = f"No new acts confirmed; {errors} notice(s) had fetch or upload errors."
    elif new:
        outcome = "new_acts"
        message = f"New acts to download: {new}"
    elif changed:
        outcome = "changed_acts"
        message = f"No new acts. Changed acts: {changed}"
    elif removed:
        outcome = "removed_acts"
        message = f"No new acts. Acts no longer published: {removed}"
    else:
        outcome = "no_changes"
        message = "No new acts to download and no changes."
    if timestamp is None:
        timestamp = datetime.now(ZoneInfo("Europe/Rome")).replace(microsecond=0).isoformat()
    return {
        "timestamp": timestamp,
        "timezone": "Europe/Rome",
        "outcome": outcome,
        "message": message,
        "counts": counts,
    }


def combined_markdown(index_report, stats_report):
    index_counts = index_report["counts"]
    stats_counts = stats_report["counts"]
    lines = [
        "# Hourly publication report",
        "",
        f"> **Result:** {stats_report['message']}",
        ">",
        f"> Checked at: {stats_report['timestamp']} ({stats_report['timezone']})",
        "",
        f"- Checked at: {stats_report['timestamp']} ({stats_report['timezone']})",
        f"- Outcome: {stats_report['outcome']}",
        f"- Result: {stats_report['message']}",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Acts in current window | {stats_counts.get('notices', 0)} |",
        f"| Acts published | {stats_counts.get('published', 0)} |",
        f"| New acts in index | {index_counts.get('new', 0)} |",
        f"| Changed acts in index | {index_counts.get('changed', 0)} |",
        f"| Acts no longer published | {index_counts.get('removed', 0)} |",
        f"| Unchanged acts | {index_counts.get('unchanged', 0)} |",
        "",
        "## Index comparison",
        "",
        markdown(index_report).split("\n", 2)[2],
    ]
    return "\n".join(lines).rstrip() + "\n"


def markdown(report):
    counts = report["counts"]
    lines = [
        "# Hourly publication check",
        "",
        f"- Checked at: {report['timestamp']} ({report['timezone']})",
        f"- Outcome: {report['outcome']}",
        f"- Result: {report['message']}",
        f"- Acts before: {counts.get('before', 0)}",
        f"- Acts after: {counts.get('after', counts.get('notices', 0))}",
        f"- New acts: {counts.get('new', 0)}",
        f"- Changed acts: {counts.get('changed', 0)}",
        f"- Acts no longer published: {counts.get('removed', 0)}",
        f"- Unchanged acts: {counts.get('unchanged', 0)}",
    ]
    return "\n".join(lines) + "\n"


def write_report(report, json_path, markdown_path=None):
    json_target = Path(json_path)
    json_target.parent.mkdir(parents=True, exist_ok=True)
    json_target.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    if markdown_path:
        markdown_target = Path(markdown_path)
        markdown_target.parent.mkdir(parents=True, exist_ok=True)
        markdown_target.write_text(markdown(report), encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compare generated indexes and report changes")
    parser.add_argument("--before", help="Index JSON before the hourly refresh")
    parser.add_argument("--after", help="Index JSON after the hourly refresh")
    parser.add_argument(
        "--stats",
        help="apt_cron.py JSON stats from a dry run or normal run",
    )
    parser.add_argument("--json-path", help="Write the JSON report to this path")
    parser.add_argument("--markdown-path", help="Write the Markdown report to this path")
    parser.add_argument(
        "--stats-for",
        help="Index path paired with --stats for a combined report",
    )
    parser.add_argument("--stdout", action="store_true", help="Print the Markdown report to stdout")
    args = parser.parse_args(argv)

    try:
        stats_report = None
        if args.stats:
            stats = json.loads(Path(args.stats).read_text(encoding="utf-8"))
            stats_report = build_stats_report(stats)
            if args.stats_for:
                index_report = build_report(_load_index(args.before), _load_index(args.stats_for))
                text = combined_markdown(index_report, stats_report)
            else:
                text = markdown(stats_report)
        elif args.before and args.after:
            report = build_report(_load_index(args.before), _load_index(args.after))
            text = markdown(report)
        else:
            parser.error("provide --before and --after, or --stats")
        report = stats_report if args.stats else report
        if args.json_path or args.markdown_path:
            write_report(report, args.json_path or "/dev/null", args.markdown_path)
        if args.stdout:
            sys.stdout.write(text)
        else:
            print(json.dumps(report, sort_keys=True))
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
