#!/usr/bin/env python3
"""
Update an EXISTING Google Sheet in place. Sheets sibling of update_doc.py.

The point: maintain a Google Sheet from a repo master, so the Sheet's URL stays
stable and tabular data lives where it belongs (sort / filter / status colors /
one-cell edits) instead of being forced into a Doc.

Two modes (mutually exclusive):

  A. Whole-tab replace (the tab is a published render of a repo markdown-table / CSV):
       python3 -m tools.google.update_sheet --account personal \\
           --sheet <id-or-url> --tab Milestones --md docs/scoreboard.md --force-whole-tab

       python3 -m tools.google.update_sheet --account personal \\
           --sheet <id-or-url> --tab Milestones --csv data/milestones.csv --force-whole-tab

     Clears the named tab and rewrites it from the master. Creates the tab if missing.
     A markdown file may contain several tables under ## headings; pass --section
     "Milestones" to pick one, or omit to use the first table in the file.
     WARNING: replaces the whole tab — manual in-Sheet edits to that tab are overwritten.

  B. Surgical cell / range update (bump a status or date; leaves the rest of the tab):
       python3 -m tools.google.update_sheet --account personal --sheet <id-or-url> \\
           --tab Milestones --set B3 "In progress" --set C3 "2026-06-05"
       python3 -m tools.google.update_sheet --account personal --sheet <id-or-url> \\
           --tab Milestones --set-range A5:B5 "Item optioned" "OPEN"

--sheet accepts a bare spreadsheetId or a full Sheets URL (…/d/<ID>/…).
A1 ranges in --set / --set-range are relative to the --tab.
"""
from __future__ import annotations

import argparse
import csv as csvmod
import io
import re
import sys
from pathlib import Path

from tools.google.auth import build_service


def _extract_id(sheet: str) -> str:
    m = re.search(r"/d/([a-zA-Z0-9_-]+)", sheet)
    return m.group(1) if m else sheet.strip()


def _parse_markdown_table(text: str, section: str | None) -> list[list[str]]:
    """Return rows (incl. header) from the first markdown table, or the table under
    the `## section` heading if section is given."""
    lines = text.splitlines()
    start = 0
    if section:
        for i, ln in enumerate(lines):
            if re.match(r"^#+\s+", ln) and section.lower() in ln.lower():
                start = i + 1
                break
        else:
            print(f"Error: section heading matching {section!r} not found.", file=sys.stderr)
            raise SystemExit(2)

    rows: list[list[str]] = []
    in_table = False
    for ln in lines[start:]:
        s = ln.strip()
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            # skip the |---|---| separator row
            if all(re.fullmatch(r":?-+:?", c or "-") for c in cells):
                in_table = True
                continue
            rows.append(cells)
            in_table = True
        elif in_table and not s.startswith("|"):
            break  # table ended
    if not rows:
        print("Error: no markdown table found.", file=sys.stderr)
        raise SystemExit(2)
    return rows


def _parse_csv(text: str) -> list[list[str]]:
    return [row for row in csvmod.reader(io.StringIO(text))]


def _read_rows(md: str | None, csv: str | None, section: str | None) -> list[list[str]]:
    if csv is not None:
        data = sys.stdin.read() if csv == "-" else Path(csv).read_text()
        return _parse_csv(data)
    data = sys.stdin.read() if md == "-" else Path(md).read_text()
    return _parse_markdown_table(data, section)


def _get_sheet_meta(svc, sid: str) -> dict:
    return svc.spreadsheets().get(
        spreadsheetId=sid, fields="properties.title,sheets.properties"
    ).execute()


def _tab_titles(meta: dict) -> dict[str, int]:
    return {
        s["properties"]["title"]: s["properties"]["sheetId"]
        for s in meta.get("sheets", [])
    }


def _ensure_tab(svc, sid: str, meta: dict, tab: str) -> dict:
    """Create the tab if it doesn't exist; return refreshed meta."""
    if tab in _tab_titles(meta):
        return meta
    svc.spreadsheets().batchUpdate(
        spreadsheetId=sid,
        body={"requests": [{"addSheet": {"properties": {"title": tab}}}]},
    ).execute()
    return _get_sheet_meta(svc, sid)


def _whole_tab_replace(svc, sid: str, tab: str, rows: list[list[str]]) -> dict:
    svc.spreadsheets().values().clear(spreadsheetId=sid, range=f"'{tab}'").execute()
    resp = svc.spreadsheets().values().update(
        spreadsheetId=sid,
        range=f"'{tab}'!A1",
        valueInputOption="USER_ENTERED",
        body={"values": rows},
    ).execute()
    # Bold the header row (best-effort; ignore if it fails).
    try:
        meta = _get_sheet_meta(svc, sid)
        gid = _tab_titles(meta)[tab]
        svc.spreadsheets().batchUpdate(
            spreadsheetId=sid,
            body={"requests": [{
                "repeatCell": {
                    "range": {"sheetId": gid, "startRowIndex": 0, "endRowIndex": 1},
                    "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                    "fields": "userEnteredFormat.textFormat.bold",
                }
            }, {
                "updateSheetProperties": {
                    "properties": {"sheetId": gid, "gridProperties": {"frozenRowCount": 1}},
                    "fields": "gridProperties.frozenRowCount",
                }
            }]},
        ).execute()
    except Exception:
        pass
    return resp


def _surgical(svc, sid: str, tab: str, sets, set_ranges) -> int:
    data = []
    for cell, value in (sets or []):
        data.append({"range": f"'{tab}'!{cell}", "values": [[value]]})
    for item in (set_ranges or []):
        rng, *vals = item
        data.append({"range": f"'{tab}'!{rng}", "values": [vals]})
    resp = svc.spreadsheets().values().batchUpdate(
        spreadsheetId=sid,
        body={"valueInputOption": "USER_ENTERED", "data": data},
    ).execute()
    return resp.get("totalUpdatedCells", 0)


def main() -> int:
    p = argparse.ArgumentParser(description="Update an existing Google Sheet in place.")
    p.add_argument("--account", choices=["work", "personal"], default="personal")
    p.add_argument("--sheet", required=True, help="Spreadsheet ID or full URL")
    p.add_argument("--tab", required=True, help="Tab (sheet) name; created if missing")
    # Whole-tab sources are mutually exclusive with each other; surgical flags can be used together.
    src = p.add_mutually_exclusive_group()
    src.add_argument("--md", help="Markdown file (or '-') → whole-tab replace from a table")
    src.add_argument("--csv", help="CSV file (or '-') → whole-tab replace")
    p.add_argument("--set", nargs=2, action="append", metavar=("A1", "VALUE"),
                   help="Surgical single-cell set (repeatable), e.g. --set B3 OPEN")
    p.add_argument("--set-range", nargs="+", action="append", metavar="RANGE V1 V2…",
                   help="Surgical row write: RANGE then values, e.g. --set-range A5:C5 Item OPEN 2026-06")
    p.add_argument("--section", help="With --md: pick the table under this ## heading")
    p.add_argument("--force-whole-tab", action="store_true",
                   help="Required to run a whole-tab --md/--csv replace (it CLOBBERS the tab incl. team "
                        "edits). Surgical --set/--set-range is the default + only unguarded path.")
    p.add_argument("--use-sa", action="store_true", help="Force SA+DWD path (work only)")
    args = p.parse_args()

    whole_tab = args.md is not None or args.csv is not None
    surgical = bool(args.set or args.set_range)
    if whole_tab and surgical:
        p.error("use either whole-tab (--md/--csv) OR surgical (--set/--set-range), not both")
    if not whole_tab and not surgical:
        p.error("provide one of --md, --csv, --set, or --set-range")
    # Surgical-only guard: whole-tab replace overwrites in-Sheet/team edits.
    if whole_tab and not args.force_whole_tab:
        p.error("Refusing whole-tab replace: it overwrites in-Sheet/team edits. Use surgical "
                "--set A1 VALUE / --set-range A1:C1 v1 v2 ... (preserves the rest). If you own this "
                "tab end-to-end and intend to clobber it, pass --force-whole-tab.")

    sid = _extract_id(args.sheet)
    svc = build_service("sheets", "v4", account=args.account, use_sa=args.use_sa or None)

    meta = _get_sheet_meta(svc, sid)
    title = meta.get("properties", {}).get("title", "?")
    meta = _ensure_tab(svc, sid, meta, args.tab)

    if args.set or args.set_range:
        n = _surgical(svc, sid, args.tab, args.set, args.set_range)
        print(f"OK surgical update on '{title}' tab '{args.tab}': {n} cell(s) updated.")
        for cell, value in (args.set or []):
            print(f"  {cell} = {value!r}")
        for item in (args.set_range or []):
            print(f"  {item[0]} = {item[1:]!r}")
        return 0

    rows = _read_rows(args.md, args.csv, args.section)
    resp = _whole_tab_replace(svc, sid, args.tab, rows)
    print(f"OK replaced tab '{args.tab}' in '{title}': "
          f"{resp.get('updatedRows', len(rows))} row(s) × "
          f"{resp.get('updatedColumns', len(rows[0]) if rows else 0)} col(s).")
    print(f"   link: https://docs.google.com/spreadsheets/d/{sid}/edit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
