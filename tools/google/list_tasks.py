#!/usr/bin/env python3
"""
List Google Tasks. Replaces mcp__gtasks__list and mcp__gtasks__list-tasklists.

Usage:
    python3 tools/google/list_tasks.py --account personal               # default list
    python3 tools/google/list_tasks.py --account personal --tasklists   # show all tasklists
    python3 tools/google/list_tasks.py --account personal --list-id <id>
    python3 tools/google/list_tasks.py --account personal --show-completed
"""
from __future__ import annotations

import argparse
import json
import sys

from tools.google.auth import build_service


def main() -> int:
    p = argparse.ArgumentParser(description="List Google Tasks.")
    p.add_argument("--account", choices=["work", "personal"], default="personal")
    p.add_argument("--tasklists", action="store_true", help="List all tasklists instead of tasks")
    p.add_argument("--all-lists", action="store_true", help="Aggregate tasks across ALL tasklists. Use this when you must not miss tasks bucketed into non-default lists.")
    p.add_argument("--list-id", help="Tasklist ID (defaults to first/primary list)")
    p.add_argument("--show-completed", action="store_true")
    p.add_argument("--show-deleted", action="store_true")
    p.add_argument("--show-hidden", action="store_true")
    p.add_argument("--max-results", type=int, default=100)
    args = p.parse_args()

    service = build_service("tasks", "v1", account=args.account, use_sa=False)

    if args.tasklists:
        resp = service.tasklists().list(maxResults=args.max_results).execute()
        json.dump(resp.get("items", []), sys.stdout, indent=2, default=str)
        print()
        return 0

    if args.all_lists:
        lists = service.tasklists().list(maxResults=50).execute().get("items", [])
        out = []
        for tl in lists:
            resp = service.tasks().list(
                tasklist=tl["id"],
                showCompleted=args.show_completed,
                showDeleted=args.show_deleted,
                showHidden=args.show_hidden,
                maxResults=args.max_results,
            ).execute()
            out.append({
                "list_id": tl["id"],
                "list_title": tl.get("title", ""),
                "items": resp.get("items", []),
            })
        json.dump({"lists": out}, sys.stdout, indent=2, default=str)
        print()
        return 0

    list_id = args.list_id
    if not list_id:
        lists = service.tasklists().list(maxResults=10).execute().get("items", [])
        if not lists:
            print("No tasklists found.", file=sys.stderr)
            return 1
        list_id = lists[0]["id"]

    resp = service.tasks().list(
        tasklist=list_id,
        showCompleted=args.show_completed,
        showDeleted=args.show_deleted,
        showHidden=args.show_hidden,
        maxResults=args.max_results,
    ).execute()
    json.dump({"list_id": list_id, "items": resp.get("items", [])}, sys.stdout, indent=2, default=str)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
