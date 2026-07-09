#!/usr/bin/env python3
"""
Send a Gmail message directly. Companion to draft_email.py.

Safety policy:
- Self-sends (recipient == authenticated account's email) are AUTO-ALLOWED.
- External sends (recipient != self) REQUIRE the explicit --allow-external flag.
  Default behavior: refuse with a clear error pointing you to draft_email.py
  for the standard external-action approval gate.

Self-send rationale: self-emails (e.g., dumping text into your own inbox for a
read-later app, sending yourself reminders, mailing a memo back to yourself as a
save-to-inbox pattern) carry no relationship or hygiene risk and should not need
a manual review gate.

External-send rationale: external sends touch counterparties / public-surface
and should run through a human approval step. The --allow-external flag exists
only as an escape hatch for cases where a send-without-draft was explicitly
authorized.

Usage (self-send):
    python3 tools/google/send_email.py --account personal \\
        --to you@example.com --subject "..." --body "..."

Usage (send an existing draft by ID — converts draft → sent):
    python3 tools/google/send_email.py --account personal \\
        --send-draft-id r-8502763183756164631

Usage (read body from file):
    python3 tools/google/send_email.py --account personal \\
        --to you@example.com --subject "..." --body-file path/to/body.txt

Usage (external send — requires explicit override):
    python3 tools/google/send_email.py --account personal \\
        --to someone@example.com --subject "..." --body "..." \\
        --allow-external
"""
from __future__ import annotations

import argparse
import base64
import html as _html
import json
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

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
) -> str:
    # multipart/alternative: text/plain fallback + text/html (rendered by Gmail,
    # not hard-wrapped). HTML part stops the staircase-wrap on store/send.
    msg = MIMEMultipart("alternative")
    msg.attach(MIMEText(body, "plain", "utf-8"))
    msg.attach(MIMEText(_body_to_html(body), "html", "utf-8"))
    msg["To"] = to
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = cc
    if bcc:
        msg["Bcc"] = bcc
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
    if references:
        msg["References"] = references
    return base64.urlsafe_b64encode(msg.as_bytes()).decode()


def _get_account_email(service) -> str:
    profile = service.users().getProfile(userId="me").execute()
    return profile.get("emailAddress", "").lower()


def _is_self_send(to: str, account_email: str) -> bool:
    recipients = [r.strip().lower() for r in to.split(",")]
    return all(r == account_email for r in recipients if r)


def main() -> int:
    p = argparse.ArgumentParser(description="Send a Gmail message. Self-sends auto-allowed; external sends require --allow-external.")
    p.add_argument("--account", choices=["work", "personal"], default="personal")
    p.add_argument("--send-draft-id", help="Send an existing draft by ID (converts draft -> sent message)")
    p.add_argument("--to", help="Recipient(s); required when not using --send-draft-id")
    p.add_argument("--cc")
    p.add_argument("--bcc")
    p.add_argument("--subject", help="Subject line; required when not using --send-draft-id")
    p.add_argument("--thread-id", help="Gmail thread ID to attach to (for in-thread replies)")
    p.add_argument("--in-reply-to", help="RFC822 Message-ID of the message being replied to")
    p.add_argument("--references", help="RFC822 References header (space-separated Message-ID chain)")
    body_grp = p.add_mutually_exclusive_group()
    body_grp.add_argument("--body", help="Body text (literal)")
    body_grp.add_argument("--body-file", help="Path to file with body text")
    p.add_argument("--allow-external", action="store_true",
                   help="Required if recipient is not the authenticated account itself. Use draft_email.py instead unless direct-send was explicitly authorized.")
    p.add_argument("--use-sa", action="store_true")
    args = p.parse_args()

    service = build_service("gmail", "v1", account=args.account, use_sa=args.use_sa or None)
    account_email = _get_account_email(service)

    if args.send_draft_id:
        # Sending an existing draft. Resolve its recipient(s) to check self-send.
        draft = service.users().drafts().get(userId="me", id=args.send_draft_id, format="metadata").execute()
        headers = draft.get("message", {}).get("payload", {}).get("headers", [])
        to_header = next((h["value"] for h in headers if h.get("name", "").lower() == "to"), "")
        if not to_header:
            print(json.dumps({"error": "Draft has no To header; cannot validate self-send safety."}), file=sys.stderr)
            return 2
        if not _is_self_send(to_header, account_email) and not args.allow_external:
            print(json.dumps({
                "error": "Refusing external send.",
                "draft_to": to_header,
                "account_email": account_email,
                "remedy": "Either review + send the draft manually in the Gmail web interface, or re-run with --allow-external if direct-send was explicitly authorized.",
            }), file=sys.stderr)
            return 3
        result = service.users().drafts().send(userId="me", body={"id": args.send_draft_id}).execute()
        out = {
            "action": "sent-from-draft",
            "message_id": result.get("id"),
            "thread_id": result.get("threadId"),
            "draft_id": args.send_draft_id,
            "to": to_header,
            "self_send": _is_self_send(to_header, account_email),
        }
        json.dump(out, sys.stdout, indent=2, default=str)
        print()
        return 0

    # Direct send (no draft).
    if not (args.to and args.subject):
        p.error("--to and --subject required when not using --send-draft-id")

    if not _is_self_send(args.to, account_email) and not args.allow_external:
        print(json.dumps({
            "error": "Refusing external send.",
            "to": args.to,
            "account_email": account_email,
            "remedy": "Use draft_email.py for external sends (review + send manually). Or re-run with --allow-external if direct-send was explicitly authorized.",
        }), file=sys.stderr)
        return 3

    if args.body_file:
        with open(args.body_file) as f:
            body_text = f.read()
    else:
        body_text = args.body or ""

    raw = _build_raw(
        to=args.to,
        subject=args.subject,
        body=body_text,
        cc=args.cc,
        bcc=args.bcc,
        in_reply_to=args.in_reply_to,
        references=args.references,
    )
    msg_obj = {"raw": raw}
    if args.thread_id:
        msg_obj["threadId"] = args.thread_id

    result = service.users().messages().send(userId="me", body=msg_obj).execute()
    out = {
        "action": "sent-direct",
        "message_id": result.get("id"),
        "thread_id": result.get("threadId"),
        "to": args.to,
        "self_send": _is_self_send(args.to, account_email),
    }
    json.dump(out, sys.stdout, indent=2, default=str)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
