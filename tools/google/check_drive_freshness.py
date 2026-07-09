#!/usr/bin/env python3
"""
Check data freshness in a Google Drive folder by inspecting the newest file's date.

Why this exists: an aggregator-pattern pipeline (some upstream source that writes
dated export files into a Drive folder on a schedule) can only forward what its
upstreams push. A "pipeline ran today" signal does NOT catch a silently-stopped
upstream — the export job keeps running and writing files, but the newest file's
*date* stops advancing. Pair every pipeline-health check with a data-freshness
check like this one.

This script lists a Drive folder, finds the newest file matching a pattern,
extracts the date, and compares it to today. It exits non-zero on drift so it
composes into shell pipelines and scheduled rollups.

Two date sources supported:
  - filename pattern (preferred — independent of file system clock)
  - Drive modifiedTime (--use-modified-time fallback)

Usage:
    # Default monitor: files named like "Export-YYYY-MM-DD" in an "Exports" folder
    python3 -m tools.google.check_drive_freshness --account personal

    # Custom folder + pattern
    python3 -m tools.google.check_drive_freshness --account personal \\
        --folder-name "Daily Exports" \\
        --filename-pattern 'export-(\\d{4}-\\d{2}-\\d{2})' \\
        --max-age-days 2

    # Folder by ID instead of name lookup
    python3 -m tools.google.check_drive_freshness --account personal \\
        --folder-id 1AbCdEfGhIjKlM --max-age-days 3

    # Fall back to Drive modifiedTime
    python3 -m tools.google.check_drive_freshness --account personal \\
        --folder-name "Some Folder" --use-modified-time --max-age-days 2

Exit codes:
    0 = fresh (newest file within --max-age-days)
    1 = stale (drift exceeds threshold) OR no matching files found
    2 = setup error (folder not found, multiple matches, auth failure, etc.)
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from typing import Optional

from googleapiclient.errors import HttpError

from tools.google.auth import build_service


DEFAULT_FOLDER_NAME = "Exports"
DEFAULT_FILENAME_PATTERN = r"Export-(\d{4}-\d{2}-\d{2})"
DEFAULT_MAX_AGE_DAYS = 2


def find_folder_id(service, folder_name: str) -> str:
    """Look up a Drive folder ID by exact name. Raises if 0 or >1 matches."""
    q = (
        f"name = '{folder_name}' "
        "and mimeType = 'application/vnd.google-apps.folder' "
        "and trashed = false"
    )
    resp = service.files().list(
        q=q,
        fields="files(id, name, parents)",
        spaces="drive",
    ).execute()
    files = resp.get("files", [])
    if not files:
        raise LookupError(f"No folder named {folder_name!r} found in Drive.")
    if len(files) > 1:
        paths = ", ".join(f"{f['id']} (parents={f.get('parents')})" for f in files)
        raise LookupError(
            f"Multiple folders named {folder_name!r}: {paths}. "
            f"Disambiguate with --folder-id."
        )
    return files[0]["id"]


def list_folder_files(service, folder_id: str) -> list[dict]:
    """List all non-trashed files directly under folder_id."""
    out: list[dict] = []
    page_token: Optional[str] = None
    while True:
        resp = service.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="nextPageToken, files(id, name, modifiedTime, mimeType)",
            pageSize=200,
            pageToken=page_token,
        ).execute()
        out.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return out


def newest_by_filename(files: list[dict], pattern: re.Pattern) -> tuple[Optional[dict], Optional[dt.date]]:
    """Return (file, parsed_date) for the file whose name regex-matches with the latest YYYY-MM-DD."""
    best_file = None
    best_date: Optional[dt.date] = None
    for f in files:
        m = pattern.search(f["name"])
        if not m:
            continue
        try:
            d = dt.date.fromisoformat(m.group(1))
        except (ValueError, IndexError):
            continue
        if best_date is None or d > best_date:
            best_file, best_date = f, d
    return best_file, best_date


def newest_by_modified_time(files: list[dict]) -> tuple[Optional[dict], Optional[dt.date]]:
    """Return (file, modified_date) for the file with the latest modifiedTime."""
    best_file = None
    best_dt: Optional[dt.datetime] = None
    for f in files:
        raw = f.get("modifiedTime")
        if not raw:
            continue
        parsed = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if best_dt is None or parsed > best_dt:
            best_file, best_dt = f, parsed
    return best_file, (best_dt.date() if best_dt else None)


def main() -> int:
    p = argparse.ArgumentParser(
        description="Check data freshness in a Google Drive folder.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--account", choices=["work", "personal"], default="personal")
    src = p.add_mutually_exclusive_group()
    src.add_argument("--folder-id", help="Drive folder ID (skips name lookup)")
    src.add_argument(
        "--folder-name",
        default=DEFAULT_FOLDER_NAME,
        help=f"Drive folder name (default: {DEFAULT_FOLDER_NAME!r})",
    )
    p.add_argument(
        "--filename-pattern",
        default=DEFAULT_FILENAME_PATTERN,
        help=(
            "Regex with one ISO-date capture group "
            f"(default: {DEFAULT_FILENAME_PATTERN!r})"
        ),
    )
    p.add_argument(
        "--use-modified-time",
        action="store_true",
        help="Use Drive modifiedTime instead of filename date (fallback for sources without dated names)",
    )
    p.add_argument(
        "--max-age-days",
        type=int,
        default=DEFAULT_MAX_AGE_DAYS,
        help=f"Max allowed gap between today and newest file (default: {DEFAULT_MAX_AGE_DAYS})",
    )
    p.add_argument("--quiet", action="store_true", help="Suppress fresh/stale line, just exit code")
    args = p.parse_args()

    if args.max_age_days < 0:
        print("--max-age-days must be >= 0", file=sys.stderr)
        return 2

    try:
        service = build_service("drive", "v3", account=args.account)
    except Exception as e:
        print(f"Auth/build error: {e}", file=sys.stderr)
        return 2

    folder_id = args.folder_id
    folder_label = args.folder_id or args.folder_name
    if not folder_id:
        try:
            folder_id = find_folder_id(service, args.folder_name)
        except LookupError as e:
            print(f"FOLDER ERROR: {e}", file=sys.stderr)
            return 2
        except HttpError as e:
            print(f"Drive API error during folder lookup: {e}", file=sys.stderr)
            return 2

    try:
        files = list_folder_files(service, folder_id)
    except HttpError as e:
        print(f"Drive API error listing folder: {e}", file=sys.stderr)
        return 2

    if not files:
        if not args.quiet:
            print(f"STALE: folder {folder_label!r} is empty")
        return 1

    if args.use_modified_time:
        newest, newest_date = newest_by_modified_time(files)
        mode = "modifiedTime"
    else:
        try:
            pattern = re.compile(args.filename_pattern)
        except re.error as e:
            print(f"Invalid --filename-pattern regex: {e}", file=sys.stderr)
            return 2
        newest, newest_date = newest_by_filename(files, pattern)
        mode = f"filename={args.filename_pattern!r}"

    if newest is None or newest_date is None:
        if not args.quiet:
            print(
                f"STALE: no files in {folder_label!r} matched {mode}; "
                f"folder has {len(files)} file(s)."
            )
        return 1

    today = dt.date.today()
    age = (today - newest_date).days

    status = "FRESH" if age <= args.max_age_days else "STALE"
    if not args.quiet:
        print(
            f"{status}: newest={newest['name']!r} date={newest_date.isoformat()} "
            f"age={age}d threshold={args.max_age_days}d folder={folder_label!r} mode={mode}"
        )

    return 0 if status == "FRESH" else 1


if __name__ == "__main__":
    sys.exit(main())
