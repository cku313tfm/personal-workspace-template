"""
Auth helper for Google API integrations.

Two paths:
  1. OAuth refresh-token flow (default for consumer Gmail and for Workspace
     accounts in Phase 1). Credentials live in secrets/google-oauth.json
     (gitignored).
  2. Service Account + Domain-Wide Delegation (optional Phase 2 for a Workspace
     account you control, where SA+DWD gives more reliable auth).
     SA key at secrets/sa-key.json (gitignored).

Account names (generic examples — map them to your own profiles below):
  - "work"           → your Workspace account (SA+DWD when configured)
  - "personal"       → your consumer Gmail (OAuth only)
  - "personal-tasks" → same consumer Gmail, Tasks API (separate OAuth client)

Usage:
    from tools.google.auth import get_credentials
    creds = get_credentials("work", api="calendar")
    service = build("calendar", "v3", credentials=creds)

The library auto-refreshes access tokens; refresh tokens are stable.

Configuration via environment (all optional):
  - WORKSPACE_DIR            → repo root (defaults to two levels above this file)
  - GOOGLE_SA_DELEGATED_USER → Workspace user the SA impersonates (e.g. you@yourdomain.com)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

# Repo root. Override with WORKSPACE_DIR; otherwise derive from this file's location.
REPO_ROOT = Path(os.environ.get("WORKSPACE_DIR", Path(__file__).resolve().parent.parent.parent))
SECRETS_DIR = REPO_ROOT / "secrets"
OAUTH_PATH = SECRETS_DIR / "google-oauth.json"
SA_KEY_PATH = SECRETS_DIR / "sa-key.json"
# Workspace user the service account impersonates (SA+DWD). Set via env; leave
# blank if you are not using the service-account path.
SA_DELEGATED_USER = os.environ.get("GOOGLE_SA_DELEGATED_USER", "")
TOKEN_URI = "https://oauth2.googleapis.com/token"

# Scope groups by API. Helpers ask for what they need; auth picks the right profile.
API_SCOPES = {
    "calendar": ["https://www.googleapis.com/auth/calendar"],
    "calendar.readonly": ["https://www.googleapis.com/auth/calendar.readonly"],
    "gmail": ["https://mail.google.com/"],
    "gmail.readonly": ["https://www.googleapis.com/auth/gmail.readonly"],
    "tasks": ["https://www.googleapis.com/auth/tasks"],
    "drive": ["https://www.googleapis.com/auth/drive"],
    "drive.readonly": ["https://www.googleapis.com/auth/drive.readonly"],
    "docs": ["https://www.googleapis.com/auth/documents"],
    "sheets": ["https://www.googleapis.com/auth/spreadsheets"],
}

# Which profile in secrets/google-oauth.json to use for each (account, api) pair.
# Add your own accounts here — each key maps to a profile in the secrets file.
PROFILE_MAP = {
    ("work", "calendar"): "work",
    ("work", "gmail"): "work",
    ("work", "drive"): "work",
    ("work", "docs"): "work",
    ("work", "sheets"): "work",
    ("personal", "calendar"): "personal",
    ("personal", "gmail"): "personal",
    ("personal", "drive"): "personal",
    ("personal", "docs"): "personal",
    ("personal", "sheets"): "personal",
    ("personal", "tasks"): "personal-tasks",
    # Tasks on the work account works only via SA+DWD (no OAuth profile).
}


def _load_oauth_profile(profile_name: str) -> dict:
    if not OAUTH_PATH.exists():
        raise FileNotFoundError(
            f"Missing {OAUTH_PATH}. Create it from your OAuth credentials "
            f"(see SETUP_GOOGLE_OAUTH.md)."
        )
    data = json.loads(OAUTH_PATH.read_text())
    profiles = data.get("profiles", {})
    if profile_name not in profiles:
        raise KeyError(
            f"Profile '{profile_name}' not in {OAUTH_PATH}. "
            f"Available: {list(profiles.keys())}"
        )
    return profiles[profile_name]


def _oauth_credentials(profile: dict):
    """Return google.oauth2.credentials.Credentials from a profile block."""
    from google.oauth2.credentials import Credentials
    return Credentials(
        token=None,
        refresh_token=profile["refresh_token"],
        token_uri=TOKEN_URI,
        client_id=profile["client"]["client_id"],
        client_secret=profile["client"]["client_secret"],
        scopes=profile["scopes"],
    )


def _sa_credentials(scopes: list[str]):
    """Return SA+DWD credentials impersonating SA_DELEGATED_USER."""
    from google.oauth2 import service_account
    if not SA_KEY_PATH.exists():
        raise FileNotFoundError(
            f"Missing {SA_KEY_PATH}. SA+DWD not configured. "
            f"Pass use_sa=False or fall back to OAuth."
        )
    if not SA_DELEGATED_USER:
        raise ValueError(
            "GOOGLE_SA_DELEGATED_USER env var is not set; cannot impersonate a "
            "Workspace user for SA+DWD. Set it or use the OAuth path."
        )
    base = service_account.Credentials.from_service_account_file(
        str(SA_KEY_PATH), scopes=scopes
    )
    return base.with_subject(SA_DELEGATED_USER)


def get_credentials(account: str, api: str, use_sa: Optional[bool] = None):
    """
    Return Google credentials ready for googleapiclient.discovery.build().

    account: "work" | "personal"
    api:     "calendar" | "gmail" | "tasks"
    use_sa:  If None, prefer SA+DWD for work account when SA key exists, else OAuth.
             If True, force SA path (raises if SA key absent or account != work).
             If False, force OAuth path.
    """
    if api not in API_SCOPES:
        # Allow ":readonly" sub-API names by stripping
        raise ValueError(f"Unknown api '{api}'. Use one of {list(API_SCOPES)}.")

    if use_sa is None:
        use_sa = (account == "work" and SA_KEY_PATH.exists())

    if use_sa:
        if account != "work":
            raise ValueError("SA+DWD only configured for the 'work' account.")
        return _sa_credentials(API_SCOPES[api])

    profile_name = PROFILE_MAP.get((account, api))
    if profile_name is None:
        raise ValueError(
            f"No OAuth profile mapped for ({account=}, {api=}). "
            f"Edit PROFILE_MAP in tools/google/auth.py."
        )
    profile = _load_oauth_profile(profile_name)
    return _oauth_credentials(profile)


def build_service(api: str, version: str, account: str, use_sa: Optional[bool] = None):
    """Convenience: get_credentials + googleapiclient.build."""
    from googleapiclient.discovery import build
    creds = get_credentials(account=account, api=api, use_sa=use_sa)
    return build(api, version, credentials=creds, cache_discovery=False)


if __name__ == "__main__":
    # Smoke: load every (account, api) pair we map.
    for (acct, api), profile in PROFILE_MAP.items():
        try:
            c = get_credentials(account=acct, api=api, use_sa=False)
            print(f"  OK  ({acct}, {api}) → profile '{profile}', {len(c.scopes)} scope(s)")
        except Exception as e:
            print(f"  FAIL ({acct}, {api}): {e}", file=sys.stderr)
    if SA_KEY_PATH.exists():
        try:
            c = get_credentials(account="work", api="calendar", use_sa=True)
            print(f"  OK  (work, calendar) via SA+DWD")
        except Exception as e:
            print(f"  FAIL SA: {e}", file=sys.stderr)
    else:
        print(f"  SKIP SA+DWD (no {SA_KEY_PATH})")
