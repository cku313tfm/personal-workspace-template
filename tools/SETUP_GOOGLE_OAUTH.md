# Google OAuth Setup

Click-path to give these helper scripts access to a personal Google account
(you@example.com) and, optionally, a Workspace account (you@yourdomain.com).
Totals ~20 min of browser time.

This walkthrough stores secrets in a 1Password vault (used by
`tools/google_creds.py`). If you'd rather keep secrets in a plain gitignored
file, put the same `client_id` / `client_secret` / `refresh_token` values into
`secrets/google-oauth.json` instead (the shape is documented in
`tools/google/README.md`) and skip the 1Password steps.

---

## Prerequisites

- 1Password desktop app open, signed in (only if using the 1Password path)
- `op` CLI installed: `brew install 1password-cli` then `op signin`
- Chrome or Firefox browser

---

## Step 1 — Create the 1Password vault (2 min)

1. Open the 1Password desktop app
2. Sidebar → **New Vault** → Name: `my-vault` (any name; match it to `OP_VAULT`)
3. Verify from terminal: `op vault list` — should show your vault

---

## Step 2 — Create the Google Cloud project (5 min)

1. Go to https://console.cloud.google.com/
2. Top bar → project selector → **New Project**
3. Name it whatever you like
4. If this is a personal account, leave org as "No organization" so the project is not tied to a Workspace org
5. Once created, make sure it's the active project (top bar selector)

### Enable APIs

Navigation menu → **APIs & Services** → **Library**. Enable the APIs you need,
e.g.:
- Gmail API
- Google Calendar API
- Google Drive API
- Google Docs API
- Google Sheets API
- Google Tasks API
- People API (this is where Contacts lives — NOT the deprecated "Contacts API")

---

## Step 3 — Configure OAuth consent screen (3 min)

APIs & Services → **OAuth consent screen**

- User Type: **External**
- App name: any name
- User support email: you@example.com
- Developer contact: you@example.com
- Save and continue

**Scopes screen:** add the scopes matching the APIs you enabled (type in the
filter to find each). For read-only access, the `.readonly` variants are enough;
for the send/edit helpers you'll want the broader scopes (see the scope list in
`tools/google/README.md`).

Save. Continue.

**Test users screen:** add every account you plan to authorize:
- you@example.com
- you@yourdomain.com

Save. The app stays in "Testing" mode — that's fine. Because we use refresh
tokens with offline access, the 7-day testing-mode token expiry does not affect
long-lived refresh tokens for test users.

---

## Step 4 — Create the OAuth Client ID (2 min)

APIs & Services → **Credentials** → **Create Credentials** → **OAuth client ID**

- Application type: **Web application** (NOT Desktop — we need to register the OAuth Playground redirect URI)
- Name: any name
- **Authorized redirect URIs:** add `https://developers.google.com/oauthplayground`
- Create

Copy the **Client ID** and **Client Secret** immediately — they show once.

Save to 1Password **now** before doing anything else:

### 1P item — `google-oauth-client`

Vault: `my-vault`
Item type: API Credential (or Secure Note if API Credential not available)

Fields:
- `client_id` = (from above)
- `client_secret` = (from above)
- `redirect_uri` = `https://developers.google.com/oauthplayground`

---

## Step 5 — Get refresh tokens via OAuth Playground (5 min, once per account)

This is the part that usually trips people up. Follow precisely.

### For the personal account (you@example.com):

1. Go to https://developers.google.com/oauthplayground
2. **Gear icon** (top right) → check **"Use your own OAuth credentials"**
3. Paste `client_id` and `client_secret` from Step 4
4. Close the gear
5. Left pane — find and check the scopes you enabled, e.g.:
   - Gmail API v1 → `https://www.googleapis.com/auth/gmail.readonly` (or `https://mail.google.com/` for send/modify)
   - Calendar API v3 → `https://www.googleapis.com/auth/calendar`
   - Google People API v1 → `https://www.googleapis.com/auth/contacts.readonly`
6. Click **Authorize APIs**
7. Sign in with **you@example.com** — you'll get a "Google hasn't verified this app" warning. Click **Advanced** → **Go to (your app) (unsafe)**. That warning only appears because the app is in Testing mode; it's safe because YOU built it.
8. Approve the scopes
9. Back in OAuth Playground — click **Exchange authorization code for tokens**
10. Copy the **Refresh token** (NOT the access token — access tokens expire in an hour, refresh tokens are long-lived)

### Save to 1Password:

### 1P item — `google-refresh-token-personal`

Vault: `my-vault`
Item type: API Credential (or Secure Note)

Fields:
- `account_email` = you@example.com
- `refresh_token` = (from OAuth Playground)
- `scopes` = `gmail.readonly contacts.readonly calendar.readonly` (list the scopes you granted)

### For the Workspace account (you@yourdomain.com):

Repeat steps 1-10 above, but sign in with **you@yourdomain.com** at step 7.

Save to 1Password:

### 1P item — `google-refresh-token-work`

Vault: `my-vault`
Item type: API Credential (or Secure Note)

Fields:
- `account_email` = you@yourdomain.com
- `refresh_token` = (from OAuth Playground)
- `scopes` = `gmail.readonly contacts.readonly calendar.readonly` (list the scopes you granted)

---

## Step 6 — Verify

Back in terminal:

```bash
op vault list | grep my-vault
op item list --vault my-vault
op item get google-oauth-client --vault my-vault
```

Should see all three items.

Then test from Python:

```bash
pip install google-auth google-auth-oauthlib google-api-python-client
python3 -m tools.google.auth                                    # validates profiles load
python3 -m tools.google.list_events --account personal --days 1 # validates calendar
python3 -m tools.google.list_events --account work --days 1
```

Each should print JSON without raising.

---

## Troubleshooting

**"Google hasn't verified this app"** — expected. App is in Testing mode. Click Advanced → Go to.

**"redirect_uri_mismatch"** — you didn't paste the OAuth Playground redirect URI into Authorized redirect URIs in Step 4. Fix and retry.

**"invalid_grant" when running the Python client** — refresh token was revoked (common if you re-authorized the same account). Re-run Step 5 for that account.

**1Password items missing** — confirm the vault name matches `OP_VAULT` exactly. `op` is case-sensitive.

---

## Why a Web OAuth client instead of Desktop? (answered)

Web is used so OAuth Playground can be the redirect target. Desktop clients
require a loopback redirect (`http://localhost:port`) which works but needs more
plumbing. Web + OAuth Playground is the minimum-ceremony path. Security-wise
they're equivalent for this use case because tokens live in your password
manager (or a gitignored secrets file), not in the client spec.
