#!/usr/bin/env python3
"""
Search Gmail messages. Replaces mcp__google-workspace*__search_emails.

Usage:
    python3 tools/google/search_emails.py --account personal --query "from:x@y.com after:2026/05/01"
    python3 tools/google/search_emails.py --account work --query "subject:NDA" --max-results 20
"""
from __future__ import annotations

import argparse
import json
import sys

from tools.google.auth import build_service


def main() -> int:
    p = argparse.ArgumentParser(description="Search Gmail messages.")
    p.add_argument("--account", choices=["work", "personal"], default="personal")
    p.add_argument("--query", required=True, help="Gmail search query (e.g. 'from:x@y.com after:2026/05/01')")
    p.add_argument("--max-results", type=int, default=25)
    p.add_argument("--label-ids", nargs="*", default=None)
    p.add_argument("--include-spam-trash", action="store_true")
    p.add_argument("--metadata", action="store_true",
                   help="Include subject/from/to/date headers (one extra API call per message)")
    p.add_argument("--use-sa", action="store_true")
    args = p.parse_args()

    service = build_service("gmail", "v1", account=args.account, use_sa=args.use_sa or None)

    list_kwargs = {
        "userId": "me",
        "q": args.query,
        "maxResults": args.max_results,
        "includeSpamTrash": args.include_spam_trash,
    }
    if args.label_ids:
        list_kwargs["labelIds"] = args.label_ids

    resp = service.users().messages().list(**list_kwargs).execute()
    messages = resp.get("messages", [])

    if args.metadata and messages:
        enriched = []
        for m in messages:
            md = service.users().messages().get(
                userId="me", id=m["id"], format="metadata",
                metadataHeaders=["Subject", "From", "To", "Date"],
            ).execute()
            headers = {h["name"]: h["value"] for h in md.get("payload", {}).get("headers", [])}
            enriched.append({
                "id": m["id"],
                "threadId": m["threadId"],
                "subject": headers.get("Subject"),
                "from": headers.get("From"),
                "to": headers.get("To"),
                "date": headers.get("Date"),
                "snippet": md.get("snippet"),
                "labelIds": md.get("labelIds", []),
            })
        messages = enriched

    json.dump(messages, sys.stdout, indent=2, default=str)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
