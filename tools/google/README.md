# tools/google — Python helpers for Google integrations

Direct Python calls to Google APIs (Gmail, Calendar, Drive, Docs, Sheets, Tasks)
using per-account OAuth refresh tokens. No MCP server required. Each helper is a
small CLI that writes JSON to stdout and exits non-zero on error.

## Account map

Accounts are just names you map to OAuth profiles in `secrets/google-oauth.json`
(see `tools/SETUP_GOOGLE_OAUTH.md`). The examples below use two generic accounts —
add or rename them to match your own setup by editing `PROFILE_MAP` in `auth.py`.

| Account name | Example email | Auth path | Scopes |
|---|---|---|---|
| `work` | you@yourdomain.com | OAuth refresh (Phase 1) → SA+DWD (Phase 2 if configured) | full Gmail + Calendar + Drive + Docs + Sheets |
| `personal` | you@example.com | OAuth refresh only (no Workspace, DWD doesn't apply) | full Gmail + Calendar + Drive + Docs + Sheets |
| `personal-tasks` | you@example.com | OAuth refresh (separate client, scoped narrowly) | Tasks read/write |

> Note on Workspace boundaries: Service Account + Domain-Wide Delegation can only
> reach users inside the same Workspace org as the SA. A separate Workspace org
> (a different domain) needs its own OAuth profile — SA+DWD cannot cross orgs.

## Where credentials live

```
secrets/                       (gitignored — never commit)
├── google-oauth.json          # OAuth refresh tokens for all accounts
└── sa-key.json                # SA key for a Workspace account (Phase 2; optional)
```

`secrets/google-oauth.json` holds one profile per account (e.g. `work`,
`personal`, `personal-tasks`). Each profile has its own OAuth client (id +
secret) and refresh token. Refresh tokens don't rotate; access tokens
auto-refresh on every API call via `google-auth`.

Shape of `secrets/google-oauth.json` (fill in your own values):

```json
{
  "profiles": {
    "personal": {
      "client": { "client_id": "<fill in your own>", "client_secret": "<fill in your own>" },
      "refresh_token": "<fill in your own>",
      "scopes": ["https://mail.google.com/", "https://www.googleapis.com/auth/calendar"]
    }
  }
}
```

Optional environment overrides (see `auth.py`):
- `WORKSPACE_DIR` — repo root (defaults to two levels above `auth.py`)
- `GOOGLE_SA_DELEGATED_USER` — the Workspace user the service account impersonates
- `SELF_ADDRESSES` — your own email addresses, comma-separated (used by `inbox_sweep.py` and self-send checks)

## Helpers

All helpers take `--account work|personal` (default `personal`) and write JSON to stdout. Errors go to stderr with non-zero exit.

| Helper | Common usage |
|---|---|
| `list_events.py` | `python3 -m tools.google.list_events --account personal --days 14` |
| `create_event.py` | `python3 -m tools.google.create_event --account personal --summary "Block" --start 2026-05-12T09:00:00 --end 2026-05-12T11:00:00 --time-zone America/New_York` |
| `search_emails.py` | `python3 -m tools.google.search_emails --account personal --query 'from:x@y.com after:2026/05/01' --metadata` |
| `read_email.py` | `python3 -m tools.google.read_email --account personal --thread-id <id>` |
| `draft_email.py` | `python3 -m tools.google.draft_email --account personal --to x@y.com --subject S --body B` |
| `send_email.py` | `python3 -m tools.google.send_email --account personal --to you@example.com --subject S --body B` (self-send auto-allowed) OR `--send-draft-id r-...` to convert an existing draft → sent |
| `inbox_sweep.py` | `python3 -m tools.google.inbox_sweep --account personal --state state/inbox-personal.json` (stateful "needs a response" triage; set `SELF_ADDRESSES` env first) |
| `list_tasks.py` | `python3 -m tools.google.list_tasks --account personal --all-lists` (aggregates ALL tasklists). Bare default = first list only. `--tasklists` = the list of lists; `--list-id <id>` = one specific list. |
| `create_task.py` | `python3 -m tools.google.create_task --account personal --title "Send X" --due 2026-05-09 --notes "..."` |
| `update_task.py` | `python3 -m tools.google.update_task --account personal --task-id <id> --status completed` |
| `download_file.py` | `python3 -m tools.google.download_file --account personal --file-id <id> --out path` |
| `check_drive_freshness.py` | `python3 -m tools.google.check_drive_freshness --account personal --folder-name "Exports" --filename-pattern 'export-(\d{4}-\d{2}-\d{2})' --max-age-days 2` (exits non-zero when the newest dated file is stale) |
| `update_doc.py` | **Edit an existing Google Doc in place — same URL, no new doc.** Mode A (whole-body replace from repo source, force-gated): `python3 -m tools.google.update_doc --account personal --doc <id-or-url> --md docs/overview.md --force-whole-body`. Mode B (surgical, preserves the rest): `... --doc <id-or-url> --replace "{{raise}}" "$25M" --replace DRAFT FINAL`. `--doc` takes a bare ID or a full Docs URL. |
| `update_sheet.py` | **Maintain an existing Google Sheet in place from a repo master — same URL.** Targets a Sheet by ID/URL + a named `--tab` (created if missing). Mode A (whole-tab replace, force-gated): `python3 -m tools.google.update_sheet --account personal --sheet <id-or-url> --tab Milestones --md docs/scoreboard.md --section Milestones --force-whole-tab`. Mode B (surgical): `... --tab Milestones --set B3 CIRCLING --set-range A5:C5 "Item" OPEN 2026-06-09`. |

### Email send policy

- **`draft_email.py`** — creates / updates drafts only. Use for any **external recipient**. You review + send manually in the Gmail web interface.
- **`send_email.py`** — sends directly. **Self-sends auto-allowed** (recipient == authenticated account email). Use cases: emailing yourself text for a read-later app / inbox-as-save-target, sending yourself a reminder, mailing a memo back to yourself.
- **External sends via `send_email.py`** — REFUSED by default. Requires the `--allow-external` flag, which you should only set when you have explicitly authorized a direct send (default external workflow is draft + manual review).
- **`send_email.py --send-draft-id <id>`** — converts an existing draft to sent. Same self-send validation applies: if the draft's `To` header is self → auto-send; else → refuse without `--allow-external`.

### Surgical-only editing for `update_doc` / `update_sheet`

Once a Google Doc or Sheet **exists**, prefer surgical edits. Whole-body
`--md`/`--html` (Docs) and whole-tab `--md`/`--csv` (Sheets) are **force-gated**
(`--force-whole-body` / `--force-whole-tab`) because a whole-body render silently
overwrites any edits made inside Google (formatting, comments, collaborator
input). The default + only unguarded path is surgical (`update_doc --replace`;
`update_sheet --set` / `--set-range`).

- **While a draft you own alone:** a repo markdown master can be the source of truth, but still prefer surgical edits once the Drive artifact exists.
- **Once shared with collaborators (Commenters/Editors added):** the Drive doc becomes the document of record. Never whole-body-overwrite a shared doc — it destroys collaborator comments + in-Google edits. Post-share updates are surgical only, and if you need a repo copy, pull FROM Drive (`download_file.py`) rather than pushing to it.

## Recovery — what to do when auth breaks

**Failure mode 1: refresh token revoked (HTTP 400 `invalid_grant`).**

Symptoms: any helper exits with `RefreshError: ('invalid_grant', ...)`. Cause: refresh token was revoked (re-auth elsewhere, password change, manual revocation).

**Recovery (~5 minutes per profile):**

1. Open https://developers.google.com/oauthplayground in a browser.
2. Gear icon (top right) → check **Use your own OAuth credentials**.
3. Paste the affected profile's `client_id` + `client_secret` from `secrets/google-oauth.json`. Close the gear.
4. In the left scope picker, select the same scopes that profile already had. A common broad set:
   - `https://mail.google.com/`
   - `https://www.googleapis.com/auth/calendar`
   - `https://www.googleapis.com/auth/contacts`
   - `https://www.googleapis.com/auth/documents`
   - `https://www.googleapis.com/auth/drive`
   - `https://www.googleapis.com/auth/drive.file`
   - `https://www.googleapis.com/auth/drive.readonly`
   - `https://www.googleapis.com/auth/gmail.modify`
   - `https://www.googleapis.com/auth/gmail.settings.basic`
   - `https://www.googleapis.com/auth/spreadsheets`
   - `https://www.googleapis.com/auth/presentations`
   - For a tasks-only profile: `https://www.googleapis.com/auth/tasks`
5. **Authorize APIs** → sign in with the affected account.
6. Click **Exchange authorization code for tokens** → copy the **Refresh token** (NOT the access token).
7. Edit `secrets/google-oauth.json`, paste the new `refresh_token` into the affected profile.
8. Smoke test:
   ```bash
   python3 -m tools.google.auth
   python3 -m tools.google.list_events --account <account> --days 1
   ```

**Failure mode 2: SA key missing or rejected (Workspace account only, Phase 2).**

Symptoms: `FileNotFoundError: secrets/sa-key.json` OR `403 unauthorized_client` from Google.

**Recovery options:**
- **Quick:** force the OAuth path on the work account: pass no `use_sa` (default falls through to OAuth when the SA key is absent), or pass `use_sa=False` explicitly. OAuth is the Phase 1 floor and always works.
- **Real fix:** re-run Phase 2 setup (a Google Cloud service account + Workspace Admin DWD authorization). Set `GOOGLE_SA_DELEGATED_USER` to the Workspace user the SA should impersonate.

**Failure mode 3: `secrets/google-oauth.json` is missing entirely.**

Cause: machine migration, accidental deletion.

**Recovery:** re-run the Failure-mode-1 steps for each profile. The OAuth
`client_id` / `client_secret` values are stable; keep a copy in your password
manager. If you lost them too, recreate an OAuth client in the Google Cloud
Console (see `tools/SETUP_GOOGLE_OAUTH.md`).

## Smoke test (run after any auth change)

```bash
python3 -m tools.google.auth                                       # validates all profiles load
python3 -m tools.google.list_events --account personal --days 1    # validates calendar
python3 -m tools.google.search_emails --account personal --query "in:inbox newer_than:1d" --max-results 1  # validates gmail
python3 -m tools.google.list_tasks --account personal --tasklists  # validates tasks
```

All four should print JSON without raising. If any one fails, see the corresponding failure mode above.
