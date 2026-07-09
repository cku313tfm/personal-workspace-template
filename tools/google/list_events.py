#!/usr/bin/env python3
"""
List Google Calendar events. Replaces mcp__google-workspace*__list_events.

Usage:
    python3 tools/google/list_events.py --account work --days 14
    python3 tools/google/list_events.py --account personal --time-min 2026-05-07T00:00:00-04:00 --time-max 2026-05-14T23:59:59-04:00
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone

from tools.google.auth import build_service


def main() -> int:
    p = argparse.ArgumentParser(description="List Google Calendar events.")
    p.add_argument("--account", choices=["work", "personal"], default="personal")
    p.add_argument("--calendar-id", default="primary")
    p.add_argument("--days", type=int, default=14, help="Days from now (ignored if --time-min/--time-max set)")
    p.add_argument("--time-min", help="ISO 8601 start (overrides --days)")
    p.add_argument("--time-max", help="ISO 8601 end (overrides --days)")
    p.add_argument("--max-results", type=int, default=250)
    p.add_argument("--single-events", action="store_true", default=True)
    p.add_argument("--use-sa", action="store_true", help="Force SA+DWD path (work only)")
    args = p.parse_args()

    if args.time_min and args.time_max:
        time_min, time_max = args.time_min, args.time_max
    else:
        now = datetime.now(timezone.utc)
        time_min = now.isoformat()
        time_max = (now + timedelta(days=args.days)).isoformat()

    service = build_service("calendar", "v3", account=args.account, use_sa=args.use_sa or None)
    resp = service.events().list(
        calendarId=args.calendar_id,
        timeMin=time_min,
        timeMax=time_max,
        maxResults=args.max_results,
        singleEvents=args.single_events,
        orderBy="startTime",
    ).execute()

    json.dump(resp.get("items", []), sys.stdout, indent=2, default=str)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
