#!/usr/bin/env python3
"""
Create or update a Gmail draft. Replaces mcp__google-workspace*__draft_email.

NEVER sends. Drafts only — you review + send in the Gmail web interface.

Usage (create):
    python3 tools/google/draft_email.py --account personal \\
        --to you@example.com --subject "Quick check" --body "Hi there..."

Usage (update existing draft):
    python3 tools/google/draft_email.py --account personal \\
        --draft-id r-3846322635216594867 --subject "Updated" --body "..."

Usage (read body from file):
    python3 tools/google/draft_email.py --account personal --to x@y.com \\
        --subject "..." --body-file path/to/body.txt

Usage (in-thread reply draft):
    python3 tools/google/draft_email.py --account personal --to x@y.com \\
        --subject "Re: ..." --body "..." --thread-id THREAD_ID \\
        --in-reply-to "<parent-message-id>" --references "<root-id> <parent-id>"
"""
from __future__ import annotations

import argparse
import base64
import html as _html
import json
import mimetypes
import os
import sys
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders

from tools.google.auth import build_service


def _body_to_html(body: str) -> str:
    """Convert a plain-text body into a Gmail-style HTML body.

    Why: Gmail hard-wraps text/plain bodies at ~70 chars on store/send (hard
    breaks, not reflowable). Sending an HTML alternative stops that — the
    recipient's client soft-wraps naturally. Paragraphs (blank-line-separated)
    become divs; single newlines become <br>.
    """
    paragraphs = body.replace("\r\n", "\n").split("\n\n")
    blocks = []
    for para in paragraphs:
        safe = _html.escape(para).replace("\n", "<br>")
        blocks.append(f"<div>{safe}</div>")
    return '<div dir="ltr">' + '<div><br></div>'.join(blocks) + "</div>"


def _build_raw(
    to: str,
    subject: str,
    body: str,
    cc: str | None = None,
    bcc: str | None = None,
    in_reply_to: str | None = None,
    references: str | None = None,
    from_addr: str | None = None,
    attachments: list[str] | None = None,
) -> str:
    # multipart/alternative: text/plain fallback + text/html (rendered by Gmail,
    # not hard-wrapped). HTML part stops the staircase-wrap on store/send.
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(body, "plain", "utf-8"))
    alt.attach(MIMEText(_body_to_html(body), "html", "utf-8"))

    if attachments:
        msg = MIMEMultipart("mixed")
        msg.attach(alt)
        for path in attachments:
            ctype, _ = mimetypes.guess_type(path)
            maintype, subtype = (ctype or "application/octet-stream").split("/", 1)
            part = MIMEBase(maintype, subtype)
            with open(path, "rb") as f:
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition", "attachment", filename=os.path.basename(path)
            )
            msg.attach(part)
    else:
        msg = alt

    msg["To"] = to
    msg["Subject"] = subject
    if from_addr:
        # Honored on send only if from_addr is a configured send-as alias on the
        # mailbox; otherwise Gmail rewrites to the primary address.
        msg["From"] = from_addr
    if cc:
        msg["Cc"] = cc
    if bcc:
        msg["Bcc"] = bcc
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
    if references:
        msg["References"] = references
    return base64.urlsafe_b64encode(msg.as_bytes()).decode()


def main() -> int:
    p = argparse.ArgumentParser(description="Create or update a Gmail draft (never sends).")
    p.add_argument("--account", choices=["work", "personal"], default="personal")
    p.add_argument("--draft-id", help="If set, update this draft instead of creating one")
    p.add_argument("--to", help="Recipient(s); required for create")
    p.add_argument("--cc")
    p.add_argument("--bcc")
    p.add_argument("--subject", help="Subject line")
    p.add_argument("--thread-id", help="Gmail thread ID to attach this draft to (for in-thread replies)")
    p.add_argument("--in-reply-to", help="RFC822 Message-ID of the message being replied to")
    p.add_argument("--references", help="RFC822 References header (space-separated Message-ID chain)")
    body_grp = p.add_mutually_exclusive_group()
    body_grp.add_argument("--body", help="Body text (literal)")
    body_grp.add_argument("--body-file", help="Path to file with body text")
    p.add_argument(
        "--from-addr",
        help="From address (must be a configured send-as alias on the mailbox, "
        "else Gmail rewrites to the primary address on send)",
    )
    p.add_argument(
        "--attach",
        action="append",
        default=[],
        help="Path to a file to attach (repeatable)",
    )
    p.add_argument("--use-sa", action="store_true")
    args = p.parse_args()

    if args.body_file:
        with open(args.body_file) as f:
            body_text = f.read()
    else:
        body_text = args.body or ""

    if not args.draft_id:
        if not (args.to and args.subject):
            p.error("--to and --subject required for create (no --draft-id)")

    service = build_service("gmail", "v1", account=args.account, use_sa=args.use_sa or None)

    for path in args.attach:
        if not os.path.isfile(path):
            p.error(f"--attach file not found: {path}")

    raw = _build_raw(
        to=args.to or "",
        subject=args.subject or "",
        body=body_text,
        cc=args.cc,
        bcc=args.bcc,
        in_reply_to=args.in_reply_to,
        references=args.references,
        from_addr=args.from_addr,
        attachments=args.attach or None,
    )
    msg_obj = {"message": {"raw": raw}}
    if args.thread_id:
        msg_obj["message"]["threadId"] = args.thread_id

    if args.draft_id:
        result = service.users().drafts().update(
            userId="me", id=args.draft_id, body=msg_obj
        ).execute()
        action = "updated"
    else:
        result = service.users().drafts().create(
            userId="me", body=msg_obj
        ).execute()
        action = "created"

    out = {
        "action": action,
        "draft_id": result.get("id"),
        "message_id": result.get("message", {}).get("id"),
        "thread_id": result.get("message", {}).get("threadId"),
    }
    json.dump(out, sys.stdout, indent=2, default=str)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
