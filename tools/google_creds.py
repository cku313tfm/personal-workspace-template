"""
Google credential loader backed by 1Password (optional alternative to
tools/google/auth.py's plain-file secrets).

Reads an OAuth client + per-account refresh tokens from a 1Password vault via
the `op` CLI, and exchanges refresh tokens for short-lived access tokens at call
time. Nothing sensitive is stored in the repo — the vault name and item names
below are placeholders you point at your own 1Password items.

Usage:
    from tools.google_creds import get_credentials
    creds = get_credentials(account="personal")  # or "work"
    # Pass creds into any googleapiclient.discovery.build(...) call

Requires:
    - 1Password desktop app running and unlocked
    - `op` CLI installed and signed in (`brew install 1password-cli`, `op signin`)
    - `pip install google-auth`

Configuration via environment (all optional — defaults are placeholders):
    - OP_VAULT        → the 1Password vault name (default: "my-vault")
    - OP_CLIENT_ITEM  → the item holding the OAuth client (default: "google-oauth-client")
"""

import os
import subprocess
import json
from google.oauth2.credentials import Credentials

# Point these at your own 1Password items (fill in / override via env).
VAULT = os.environ.get("OP_VAULT", "my-vault")
CLIENT_ITEM = os.environ.get("OP_CLIENT_ITEM", "google-oauth-client")
TOKEN_ITEMS = {
    "personal": "google-refresh-token-personal",
    "work": "google-refresh-token-work",
}
TOKEN_URI = "https://oauth2.googleapis.com/token"


def _op_get(item: str, field: str) -> str:
    """Read a single field from a 1Password item in the configured vault."""
    result = subprocess.run(
        ["op", "item", "get", item, "--vault", VAULT, "--fields", field, "--reveal"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def get_credentials(account: str) -> Credentials:
    """
    Return a google.oauth2.credentials.Credentials object ready to pass into
    googleapiclient.discovery.build(...).

    The google-auth library will auto-refresh the access token on first API call
    and on expiry. Refresh tokens don't rotate on every call, so no write-back
    is needed — but if Google ever invalidates one, re-run Step 5 of
    SETUP_GOOGLE_OAUTH.md for that account.
    """
    if account not in TOKEN_ITEMS:
        raise ValueError(f"Unknown account '{account}'. Use 'personal' or 'work'.")

    client_id = _op_get(CLIENT_ITEM, "client_id")
    client_secret = _op_get(CLIENT_ITEM, "client_secret")
    refresh_token = _op_get(TOKEN_ITEMS[account], "refresh_token")
    scopes_str = _op_get(TOKEN_ITEMS[account], "scopes")
    scopes = scopes_str.split()
    # Scopes field holds short names; expand to full URIs
    scopes = [
        s if s.startswith("https://") else f"https://www.googleapis.com/auth/{s}"
        for s in scopes
    ]

    return Credentials(
        token=None,  # Will be fetched on first call
        refresh_token=refresh_token,
        token_uri=TOKEN_URI,
        client_id=client_id,
        client_secret=client_secret,
        scopes=scopes,
    )


if __name__ == "__main__":
    # Smoke test: load both accounts' creds, don't hit any API
    import sys

    for acct in ("personal", "work"):
        try:
            c = get_credentials(acct)
            print(f"[{acct}] OK — scopes: {c.scopes}")
        except subprocess.CalledProcessError as e:
            print(f"[{acct}] 1P read failed: {e.stderr.strip()}", file=sys.stderr)
        except Exception as e:
            print(f"[{acct}] error: {e}", file=sys.stderr)
