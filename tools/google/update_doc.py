#!/usr/bin/env python3
"""
Update an EXISTING Google Doc in place.

The point of this helper: stop creating new docs (or copy-pasting) on every revision.
It edits the doc at a given file ID, so the URL / shareable link stays stable.

Two modes (mutually exclusive):

  A. Whole-body replace (the doc is a published render of repo markdown/HTML):
       python3 -m tools.google.update_doc --account personal \\
           --doc 1AbC...xyz --md docs/overview.md --force-whole-body

       python3 -m tools.google.update_doc --account personal \\
           --doc <url-or-id> --html out.html --force-whole-body

     Reads markdown (converted via pandoc if on PATH) or HTML, uploads it to the
     existing Doc via Drive files.update, and Google re-imports/converts in place.
     WARNING: this REPLACES the entire doc body — any edits made inside Google Docs
     are overwritten. It is SURGICAL-ONLY by default: this mode requires an explicit
     --force-whole-body flag. Prefer mode B for every edit to an existing Doc.

  B. Targeted find/replace (surgical; preserves the rest of the doc + formatting):
       python3 -m tools.google.update_doc --account personal --doc <url-or-id> \\
           --replace "{{raise}}" "$25M" \\
           --replace "Status: DRAFT" "Status: FINAL"

     Uses the Docs API replaceAllText. Repeatable. Leaves everything else untouched.

--doc accepts a bare file ID or a full Docs URL (…/d/<ID>/…).
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from tools.google.auth import build_service

DOC_MIME = "application/vnd.google-apps.document"


def _extract_id(doc: str) -> str:
    """Accept a bare ID or a Docs/Drive URL and return the file ID."""
    m = re.search(r"/d/([a-zA-Z0-9_-]+)", doc)
    if m:
        return m.group(1)
    return doc.strip()


def _read_source(md: str | None, html: str | None) -> str:
    """Return HTML string for the whole-body replace, from --md or --html."""
    if html is not None:
        data = sys.stdin.read() if html == "-" else Path(html).read_text()
        return data
    # markdown path
    md_text = sys.stdin.read() if md == "-" else Path(md).read_text()
    if not shutil.which("pandoc"):
        print(
            "Error: --md needs pandoc on PATH to convert markdown -> HTML "
            "(or pass --html with pre-converted HTML).",
            file=sys.stderr,
        )
        raise SystemExit(2)
    out = subprocess.run(
        ["pandoc", "--from", "gfm", "--to", "html"],
        input=md_text,
        capture_output=True,
        text=True,
    )
    if out.returncode != 0:
        print(f"Error: pandoc failed: {out.stderr}", file=sys.stderr)
        raise SystemExit(2)
    return out.stdout


def _replace_all_body(account: str, doc_id: str, html: str, use_sa, title: str | None = None) -> dict:
    from googleapiclient.http import MediaFileUpload

    drive = build_service("drive", "v3", account=account, use_sa=use_sa)
    # Confirm the target is actually a Google Doc before clobbering it.
    meta = drive.files().get(
        fileId=doc_id, fields="id,name,mimeType", supportsAllDrives=True
    ).execute()
    if meta.get("mimeType") != DOC_MIME:
        print(
            f"Error: file {doc_id} is mimeType '{meta.get('mimeType')}', not a Google Doc. "
            "Refusing to replace its body.",
            file=sys.stderr,
        )
        raise SystemExit(2)

    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as fh:
        fh.write(html)
        tmp = fh.name
    try:
        media = MediaFileUpload(tmp, mimetype="text/html", resumable=False)
        body = {"name": title} if title else None
        updated = drive.files().update(
            fileId=doc_id,
            body=body,
            media_body=media,
            supportsAllDrives=True,
            fields="id,name,modifiedTime,webViewLink",
        ).execute()
    finally:
        Path(tmp).unlink(missing_ok=True)
    return updated


def _find_replace(account: str, doc_id: str, pairs, match_case: bool, use_sa) -> dict:
    docs = build_service("docs", "v1", account=account, use_sa=use_sa)
    requests = [
        {
            "replaceAllText": {
                "containsText": {"text": find, "matchCase": match_case},
                "replaceText": rep,
            }
        }
        for find, rep in pairs
    ]
    resp = docs.documents().batchUpdate(
        documentId=doc_id, body={"requests": requests}
    ).execute()
    return resp


def main() -> int:
    p = argparse.ArgumentParser(description="Update an existing Google Doc in place.")
    p.add_argument("--account", choices=["work", "personal"], default="personal")
    p.add_argument("--doc", required=True, help="Google Doc file ID or full URL")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--md", help="Markdown file (or '-' for stdin) → replaces whole body")
    src.add_argument("--html", help="HTML file (or '-' for stdin) → replaces whole body")
    src.add_argument(
        "--replace",
        nargs=2,
        action="append",
        metavar=("FIND", "REPLACE"),
        help="Targeted find/replace (repeatable). Preserves the rest of the doc.",
    )
    p.add_argument("--no-match-case", action="store_true", help="Case-insensitive find/replace")
    p.add_argument("--title", help="With --md/--html: also rename the Doc to this title")
    p.add_argument("--force-whole-body", action="store_true",
                   help="Required to run a whole-body --md/--html replace (it CLOBBERS in-Doc edits). "
                        "Surgical --replace is the default + only unguarded path.")
    p.add_argument("--use-sa", action="store_true", help="Force SA+DWD path (work only)")
    args = p.parse_args()

    doc_id = _extract_id(args.doc)
    use_sa = args.use_sa or None

    # Surgical-only guard: whole-body replace destroys any edits made inside
    # Google Docs. Force it to be a deliberate, explicit choice.
    if (args.md is not None or args.html is not None) and not args.force_whole_body:
        print(
            "Refusing whole-body replace: it overwrites all in-Doc edits. "
            "Use surgical --replace FIND REPLACE (preserves formatting). "
            "If you genuinely own this Doc end-to-end and intend to clobber it, pass --force-whole-body.",
            file=sys.stderr,
        )
        return 2

    if args.replace:
        resp = _find_replace(
            args.account, doc_id, args.replace, not args.no_match_case, use_sa
        )
        replies = resp.get("replies", [])
        total = sum(r.get("replaceAllText", {}).get("occurrencesChanged", 0) for r in replies)
        print(f"OK find/replace on {doc_id}: {len(args.replace)} rule(s), {total} occurrence(s) changed.")
        for (find, rep), r in zip(args.replace, replies):
            n = r.get("replaceAllText", {}).get("occurrencesChanged", 0)
            print(f"  {n:>4}× {find!r} -> {rep!r}")
        return 0

    html = _read_source(args.md, args.html)
    updated = _replace_all_body(args.account, doc_id, html, use_sa, title=args.title)
    print(f"OK replaced body of '{updated.get('name')}' ({doc_id})")
    print(f"   modified: {updated.get('modifiedTime')}")
    print(f"   link:     {updated.get('webViewLink')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
