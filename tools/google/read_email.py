#!/usr/bin/env python3
"""
Read a Gmail thread or message. Replaces mcp__google-workspace*__read_email.

Usage:
    python3 tools/google/read_email.py --account personal --thread-id 195a1b2c3d4e5f
    python3 tools/google/read_email.py --account personal --message-id 195abc... --format full
"""
from __future__ import annotations

import argparse
import base64
import json
import sys

from tools.google.auth import build_service


def _decode_part(part: dict) -> str | None:
    """Decode a single MIME part into UTF-8 text, if it's text."""
    body = part.get("body", {})
    data = body.get("data")
    if not data:
        return None
    try:
        raw = base64.urlsafe_b64decode(data + "==")
        return raw.decode("utf-8", errors="replace")
    except Exception:
        return None


def _walk_parts(payload: dict, mime_filter: str | None = None) -> list[dict]:
    """Flatten nested MIME parts into a list with decoded text."""
    out = []
    parts = payload.get("parts") or [payload]
    for part in parts:
        if part.get("parts"):
            out.extend(_walk_parts(part, mime_filter))
            continue
        mime = part.get("mimeType", "")
        if mime_filter and not mime.startswith(mime_filter):
            continue
        out.append({
            "mimeType": mime,
            "filename": part.get("filename") or None,
            "body": _decode_part(part),
        })
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Read a Gmail thread or message.")
    p.add_argument("--account", choices=["work", "personal"], default="personal")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--thread-id")
    g.add_argument("--message-id")
    p.add_argument("--format", choices=["minimal", "metadata", "full"], default="full")
    p.add_argument("--text-only", action="store_true",
                   help="Decode and return only text/plain bodies")
    p.add_argument("--use-sa", action="store_true")
    args = p.parse_args()

    service = build_service("gmail", "v1", account=args.account, use_sa=args.use_sa or None)

    if args.thread_id:
        thread = service.users().threads().get(
            userId="me", id=args.thread_id, format=args.format,
        ).execute()
        messages = thread.get("messages", [])
    else:
        msg = service.users().messages().get(
            userId="me", id=args.message_id, format=args.format,
        ).execute()
        messages = [msg]

    if args.format == "full":
        for m in messages:
            payload = m.get("payload", {})
            if args.text_only:
                m["text_parts"] = _walk_parts(payload, mime_filter="text/plain")
            else:
                m["text_parts"] = _walk_parts(payload, mime_filter="text/")

    json.dump({"messages": messages}, sys.stdout, indent=2, default=str)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
