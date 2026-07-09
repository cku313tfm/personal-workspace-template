#!/usr/bin/env python3
"""
Stateful inbox sweep for a "response-needed" triage.

Scans an inbox for NEW human-sender messages since the last sweep (watermark),
skips threads you already replied to (last-message-from-you check — the mandatory
in:sent guard), and prints candidates for a human (or agent) to judge. The caller
decides response-needed vs FYI; this helper only does the deterministic parts.

Configuration:
    Your own email addresses (used to skip self-sent messages and detect
    already-replied threads) are read from the SELF_ADDRESSES env var,
    comma-separated. Fill in your own, e.g.:
        export SELF_ADDRESSES="you@example.com,you@work.example.com"

Usage:
    # Scan (read-only) — prints JSON candidates newer than the watermark
    python3 -m tools.google.inbox_sweep --account personal --state state/inbox-personal.json

    # After surfacing, advance the watermark + log instrumentation
    python3 -m tools.google.inbox_sweep --account personal --state state/inbox-personal.json \
        --advance --scanned 12 --surfaced 3

State file (JSON): {"watermark_epoch": int, "history": [{"date", "scanned", "surfaced"}]}
History is pruned past 30 days.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tools.google.auth import build_service

# Your own addresses — set via env (comma-separated). Fill in your own.
SELF_ADDRESSES = {
    a.strip().lower()
    for a in os.environ.get("SELF_ADDRESSES", "you@example.com").split(",")
    if a.strip()
}

# Automation senders never reach the judgment layer (exclude by construction).
AUTOMATION_SENDER_RE = re.compile(
    r"(no-?reply|donotreply|notifications?@|mailer-daemon|bounce[s]?@|"
    r"newsletters?@|updates@|alerts@|digest@|marketing@|promo|daily-report@|"
    r"communications@|reservations@|receipts?@)",
    re.I,
)

DEFAULT_LOOKBACK_DAYS = 3
HISTORY_RETENTION_DAYS = 30


def load_state(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {"watermark_epoch": int(time.time()) - DEFAULT_LOOKBACK_DAYS * 86400, "history": []}


def save_state(path: Path, state: dict) -> None:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=HISTORY_RETENTION_DAYS)).strftime("%Y-%m-%d")
    state["history"] = [h for h in state.get("history", []) if h.get("date", "") >= cutoff]
    path.write_text(json.dumps(state, indent=2) + "\n")


def header(msg: dict, name: str) -> str:
    for h in msg.get("payload", {}).get("headers", []):
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def sender_email(from_header: str) -> str:
    m = re.search(r"<([^>]+)>", from_header)
    return (m.group(1) if m else from_header).strip().lower()


def main() -> int:
    p = argparse.ArgumentParser(description="Stateful response-needed inbox sweep.")
    p.add_argument("--account", choices=["personal", "work"], required=True)
    p.add_argument("--state", required=True, help="Path to the per-inbox JSON state file")
    p.add_argument("--max", type=int, default=20, help="Cap on candidates (newest first)")
    p.add_argument("--extra-exclude", default="", help="Extra Gmail query terms, e.g. '-label:some-label'")
    p.add_argument("--advance", action="store_true", help="Advance watermark to now + log counts (no scan)")
    p.add_argument("--scanned", type=int, default=0)
    p.add_argument("--surfaced", type=int, default=0)
    args = p.parse_args()

    state_path = Path(args.state)
    state = load_state(state_path)

    if args.advance:
        state["watermark_epoch"] = int(time.time())
        state.setdefault("history", []).append(
            {"date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
             "scanned": args.scanned, "surfaced": args.surfaced}
        )
        save_state(state_path, state)
        print(json.dumps({"action": "advanced", "watermark_epoch": state["watermark_epoch"]}))
        return 0

    svc = build_service("gmail", "v1", account=args.account, use_sa=False)
    query = f"in:inbox after:{state['watermark_epoch']}"
    if args.account == "personal":
        # Consumer Gmail: exclude the non-primary category tabs so marketing/
        # updates/social never reach the judgment layer. (`category:primary`
        # itself may not resolve on a consumer account, so exclude the others
        # instead.) Workspace accounts have no category tabs and rely on the
        # sender regex alone.
        query += (" -category:promotions -category:social"
                  " -category:updates -category:forums")
    if args.extra_exclude:
        query += f" {args.extra_exclude}"

    resp = svc.users().messages().list(userId="me", q=query, maxResults=100).execute()
    msg_refs = resp.get("messages", [])

    candidates, seen_threads, scanned = [], set(), 0
    for ref in msg_refs:
        if len(candidates) >= args.max:
            break
        if ref["threadId"] in seen_threads:
            continue
        seen_threads.add(ref["threadId"])
        scanned += 1

        msg = svc.users().messages().get(
            userId="me", id=ref["id"], format="metadata",
            metadataHeaders=["From", "Subject", "Date"],
        ).execute()
        frm = header(msg, "From")
        addr = sender_email(frm)
        if addr in SELF_ADDRESSES or AUTOMATION_SENDER_RE.search(addr):
            continue

        # Reply guard: skip if the LAST non-draft message in the thread is from you.
        thread = svc.users().threads().get(
            userId="me", id=ref["threadId"], format="metadata", metadataHeaders=["From"],
        ).execute()
        thread_msgs = [m for m in thread.get("messages", []) if "DRAFT" not in m.get("labelIds", [])]
        if thread_msgs and sender_email(header(thread_msgs[-1], "From")) in SELF_ADDRESSES:
            continue

        internal_ms = int(msg.get("internalDate", "0"))
        age_days = round((time.time() - internal_ms / 1000) / 86400, 1)
        candidates.append({
            "id": ref["id"],
            "threadId": ref["threadId"],
            "from": frm,
            "subject": header(msg, "Subject"),
            "date": header(msg, "Date"),
            "age_days": age_days,
            "snippet": msg.get("snippet", "")[:160],
        })

    print(json.dumps({
        "account": args.account,
        "watermark_epoch": state["watermark_epoch"],
        "threads_scanned": scanned,
        "candidates": candidates,
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
