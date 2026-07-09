#!/usr/bin/env python3
"""
Update or complete a Google Task. Replaces mcp__gtasks__update.

Usage (mark complete):
    python3 tools/google/update_task.py --account personal \\
        --task-id <id> --status completed

Usage (edit):
    python3 tools/google/update_task.py --account personal \\
        --task-id <id> --title "New title" --due 2026-05-12 --notes "..."

Usage (delete):
    python3 tools/google/update_task.py --account personal \\
        --task-id <id> --delete
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from tools.google.auth import build_service


def _normalize_due(due: str) -> str:
    if "T" in due:
        return due
    dt = datetime.strptime(due, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def main() -> int:
    p = argparse.ArgumentParser(description="Update or complete a Google Task.")
    p.add_argument("--account", choices=["work", "personal"], default="personal")
    p.add_argument("--task-id", required=True)
    p.add_argument("--list-id", help="Tasklist ID (defaults to first/primary)")
    p.add_argument("--title")
    p.add_argument("--notes")
    p.add_argument("--due")
    p.add_argument("--status", choices=["needsAction", "completed"])
    p.add_argument("--delete", action="store_true")
    args = p.parse_args()

    service = build_service("tasks", "v1", account=args.account, use_sa=False)

    list_id = args.list_id
    if not list_id:
        lists = service.tasklists().list(maxResults=10).execute().get("items", [])
        if not lists:
            print("No tasklists found.", file=sys.stderr)
            return 1
        list_id = lists[0]["id"]

    if args.delete:
        service.tasks().delete(tasklist=list_id, task=args.task_id).execute()
        print(json.dumps({"action": "deleted", "task_id": args.task_id}))
        return 0

    # Patch only the fields supplied
    body = {}
    if args.title is not None:
        body["title"] = args.title
    if args.notes is not None:
        body["notes"] = args.notes
    if args.due is not None:
        body["due"] = _normalize_due(args.due)
    if args.status is not None:
        body["status"] = args.status
        if args.status == "completed":
            body["completed"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    if not body:
        print("No fields to update; pass --title/--notes/--due/--status or --delete.", file=sys.stderr)
        return 2

    task = service.tasks().patch(tasklist=list_id, task=args.task_id, body=body).execute()
    json.dump({"action": "updated", "list_id": list_id, "task": task}, sys.stdout, indent=2, default=str)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
