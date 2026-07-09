#!/usr/bin/env python3
"""
Download a Google Drive file. Replaces mcp__google-workspace*__download_file.

Handles both binary files (PDF, XLSX, etc.) via the get_media API, and Google-native
formats (Docs/Sheets/Slides) via the export API.

Usage:
    # Download an XLSX/PDF/binary by file ID
    python3 tools/google/download_file.py --account personal \\
        --file-id 1Llv6qqdJeRUTIk0v98otsfbM_s43PB68 --out budget.xlsx

    # Export a Google Doc as text
    python3 tools/google/download_file.py --account personal \\
        --file-id <google-doc-id> --export text/plain --out doc.txt

    # Stdout instead of file
    python3 tools/google/download_file.py --account personal --file-id ... --stdout
"""
from __future__ import annotations

import argparse
import io
import sys

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from tools.google.auth import build_service


def main() -> int:
    p = argparse.ArgumentParser(description="Download a Google Drive file.")
    p.add_argument("--account", choices=["work", "personal"], default="personal")
    p.add_argument("--file-id", required=True)
    p.add_argument("--out", help="Output path (mutually exclusive with --stdout)")
    p.add_argument("--stdout", action="store_true", help="Write bytes to stdout")
    p.add_argument("--export", help="MIME type for Google-native export (e.g. text/plain, application/pdf)")
    p.add_argument("--use-sa", action="store_true")
    args = p.parse_args()

    if not args.out and not args.stdout:
        p.error("--out or --stdout required")
    if args.out and args.stdout:
        p.error("--out and --stdout mutually exclusive")

    service = build_service("drive", "v3", account=args.account, use_sa=args.use_sa or None)

    try:
        if args.export:
            request = service.files().export_media(fileId=args.file_id, mimeType=args.export)
        else:
            request = service.files().get_media(fileId=args.file_id)

        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        data = buf.getvalue()
    except HttpError as e:
        print(f"Drive API error: {e}", file=sys.stderr)
        return 1

    if args.stdout:
        sys.stdout.buffer.write(data)
    else:
        with open(args.out, "wb") as f:
            f.write(data)
        print(f"Wrote {len(data)} bytes to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
