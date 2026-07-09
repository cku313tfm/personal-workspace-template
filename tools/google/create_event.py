#!/usr/bin/env python3
"""
Create a Google Calendar event. Companion to list_events.py.

Usage:
    python3 -m tools.google.create_event --account personal \\
        --summary "Application focus block" \\
        --start 2026-05-12T09:00:00 \\
        --end 2026-05-12T11:00:00 \\
        --time-zone America/New_York

    python3 -m tools.google.create_event --account personal \\
        --summary "Workout" \\
        --start 2026-05-15 --all-day

Start / end format:
    Timed event:   ISO 8601 local time, e.g. 2026-05-12T09:00:00 (paired with --time-zone)
                   OR ISO 8601 with offset, e.g. 2026-05-12T09:00:00-04:00
    All-day event: date only, e.g. 2026-05-15 (use --all-day; --end optional, defaults to start+1day)
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta

from tools.google.auth import build_service


def _parse_dt_or_date(value: str) -> tuple[str, bool]:
    """Return (iso_value, is_date_only)."""
    try:
        # Date-only?
        date.fromisoformat(value)
        return value, True
    except ValueError:
        pass
    try:
        datetime.fromisoformat(value)
        return value, False
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"Invalid date/datetime: {value!r}") from e


def main() -> int:
    p = argparse.ArgumentParser(description="Create a Google Calendar event.")
    p.add_argument("--account", choices=["work", "personal"], default="personal")
    p.add_argument("--calendar-id", default="primary")
    p.add_argument("--summary", required=True, help="Event title")
    p.add_argument("--description", default=None)
    p.add_argument("--location", default=None)
    p.add_argument("--start", required=True, help="ISO 8601 datetime or YYYY-MM-DD for all-day")
    p.add_argument("--end", default=None, help="ISO 8601 datetime or YYYY-MM-DD (defaults to start+1h for timed, start+1day for all-day)")
    p.add_argument("--time-zone", default="America/New_York", help="IANA time zone for naive timestamps")
    p.add_argument("--all-day", action="store_true", help="Treat as all-day event (start/end as dates)")
    p.add_argument("--attendees", nargs="*", default=[], help="Email addresses to invite")
    p.add_argument("--use-sa", action="store_true", help="Force SA+DWD path (work only)")
    args = p.parse_args()

    start_value, start_is_date = _parse_dt_or_date(args.start)
    all_day = args.all_day or start_is_date

    if args.end is None:
        if all_day:
            # All-day: end is next day (exclusive)
            d = date.fromisoformat(start_value)
            end_value = (d + timedelta(days=1)).isoformat()
            end_is_date = True
        else:
            # Timed default: start + 1 hour
            dt = datetime.fromisoformat(start_value)
            end_value = (dt + timedelta(hours=1)).isoformat()
            end_is_date = False
    else:
        end_value, end_is_date = _parse_dt_or_date(args.end)

    if all_day != (start_is_date and end_is_date):
        print(
            "Error: start and end must both be date-only when --all-day is set, "
            "and both must be timed otherwise.",
            file=sys.stderr,
        )
        return 2

    event_body: dict = {"summary": args.summary}
    if args.description:
        event_body["description"] = args.description
    if args.location:
        event_body["location"] = args.location
    if args.attendees:
        event_body["attendees"] = [{"email": a} for a in args.attendees]

    if all_day:
        event_body["start"] = {"date": start_value}
        event_body["end"] = {"date": end_value}
    else:
        event_body["start"] = {"dateTime": start_value, "timeZone": args.time_zone}
        event_body["end"] = {"dateTime": end_value, "timeZone": args.time_zone}

    service = build_service("calendar", "v3", account=args.account, use_sa=args.use_sa or None)
    created = service.events().insert(calendarId=args.calendar_id, body=event_body).execute()
    json.dump(created, sys.stdout, indent=2, default=str)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
