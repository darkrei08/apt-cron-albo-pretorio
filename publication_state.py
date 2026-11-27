#!/usr/bin/env python3
"""Seed publication state from the committed generated index."""

import argparse
import json
import sys
from pathlib import Path

import apt_cron


def state_from_index(index):
    rows = index.get("notices")
    if not isinstance(rows, list):
        raise RuntimeError("index notices must be a list")
    state = apt_cron.empty_state()
    for row in rows:
        key = apt_cron.notice_key(row)
        fingerprint = apt_cron.fingerprint(row)
        document_url = row.get("document_url")
        attachments = row.get("attachment_urls")
        links = {
            "document_url": document_url if apt_cron.public_url(document_url) else None,
            "attachment_urls": [
                url for url in (attachments or []) if apt_cron.public_url(url)
            ],
        }
        state["notices"][key] = fingerprint
        state["sent_messages"][key] = fingerprint
        state["attachments"][key] = links
        for url in [links["document_url"]] + links["attachment_urls"]:
            if url:
                state["sent_documents"][url] = key
    return state


def main(argv=None):
    parser = argparse.ArgumentParser(description="Seed state from generated index")
    parser.add_argument("--index", required=True, help="Generated index JSON")
    parser.add_argument("--state", required=True, help="State JSON to write")
    args = parser.parse_args(argv)
    try:
        index = json.loads(Path(args.index).read_text(encoding="utf-8"))
        state = state_from_index(index)
        apt_cron.save_state(args.state, state)
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
