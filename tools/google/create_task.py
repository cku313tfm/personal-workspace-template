#!/usr/bin/env python3
"""
Create a Google Task. Replaces mcp__gtasks__create.

Usage:
    python3 tools/google/create_task.py --account personal \\
        --title "Send follow-up" --due 2026-05-09 --notes "you@example.com"
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from tools.google.auth import build_service


def _normalize_due(due: str) -> str:
    """Accept YYYY-MM-DD or full RFC3339; return RFC3339 in UTC.
    Google Tasks API stores due-dates as midnight UTC; ignores time component."""
    if "T" in due:
        return due  # already RFC3339
    # YYYY-MM-DD → 00:00:00Z that day
    dt = datetime.strptime(due, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def main() -> int:
    p = argparse.ArgumentParser(description="Create a Google Task.")
    p.add_argument("--account", choices=["work", "personal"], default="personal")
    p.add_argument("--title", required=True)
    p.add_argument("--notes")
    p.add_argument("--due", help="YYYY-MM-DD or RFC3339")
    p.add_argument("--list-id", help="Tasklist ID (defaults to first/primary)")
    p.add_argument("--parent", help="Parent task ID (creates as subtask)")
    p.add_argument("--previous", help="Previous-sibling task ID (for ordering)")
    args = p.parse_args()

    service = build_service("tasks", "v1", account=args.account, use_sa=False)

    list_id = args.list_id
    if not list_id:
        lists = service.tasklists().list(maxResults=10).execute().get("items", [])
        if not lists:
            print("No tasklists found.", file=sys.stderr)
            return 1
        list_id = lists[0]["id"]

    body = {"title": args.title}
    if args.notes:
        body["notes"] = args.notes
    if args.due:
        body["due"] = _normalize_due(args.due)

    insert_kwargs = {"tasklist": list_id, "body": body}
    if args.parent:
        insert_kwargs["parent"] = args.parent
    if args.previous:
        insert_kwargs["previous"] = args.previous

    task = service.tasks().insert(**insert_kwargs).execute()
    json.dump({"list_id": list_id, "task": task}, sys.stdout, indent=2, default=str)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
