# Google sign-in setup (OAuth client for ResolveAI)

Last checked against the Google Cloud console layout of "Google Auth Platform" (Branding, Audience, Data Access, Clients). Menu names move occasionally; the concepts do not.

## What we are building

Sign-in uses **django-allauth's Google provider with the OAuth 2.0 authorization code flow and PKCE** (full-page redirects, no Google JavaScript on the page):

1. The login button is a plain link to `GET /api/auth/google/start/`, which remembers the "remember me" choice and redirects to allauth's Google login URL.
2. allauth keeps `state` and the PKCE verifier in the server-side session (first-party `SameSite=Lax` session cookie) and redirects to Google.
3. Google redirects the browser back with `?code=...&state=...` to `GET /api/auth/google/login/callback/` (a top-level GET, so the Lax cookie is sent).
4. allauth checks `state`, exchanges the code with the client secret, validates the ID token, and logs the user in; our adapter then redirects to the app (or to `/login?google_error=...` on failure).

Scopes: `openid email profile` plus `gmail.send` (send mail) and `gmail.readonly` (read mail for the inbound sync). There is **one** flow: Gmail access is requested at sign-in with offline access, and the server keeps the refresh token encrypted. Users may untick the Gmail permissions and still sign in; Gmail is then shown as not connected. See the Gmail section below.

## Why not the Google button / popup (lessons from project-management)

The previous project first rendered Google's "Sign in with Google" button (Google Identity Services, a script + iframe + popup). Its final code abandoned that for a full-page redirect, with comments saying a plain navigation means "no blocker or iframe can get in the way". Reasons this approach fails in some browsers (inferred from that code and known browser behaviour; I did not see a bug report, so tell me which browsers failed if you remember):

| Failure | Affects | How this design avoids it |
| --- | --- | --- |
| Script (`accounts.google.com/gsi/client`) blocked by ad/tracker blockers, Brave Shields, corporate filters | Brave, Firefox strict, extensions | No Google script is loaded |
| Button iframe / One Tap relies on third-party cookies or FedCM, which are restricted or being phased out | Safari (ITP), Firefox, Chrome with cookies blocked, Incognito | No iframe; only top-level navigation |
| Popups blocked or closed by the browser | iOS Safari, in-app browsers | No popup |
| `form_post` callback is a cross-site POST, so the state cookie needs `SameSite=None; Secure`, which Safari refuses on `http://localhost` and which some browsers drop | Safari on localhost, privacy modes | The callback is a GET, so the `SameSite=Lax` session cookie works everywhere, including plain-HTTP localhost |
| Google's button localizes its own label and accessible name | Non-English Google sessions | We render our own button |

Known limits that remain: in-app browsers (Instagram, LinkedIn, some embedded webviews) are blocked by Google itself ("disallowed_useragent"); users must open the link in their normal browser. We show a hint on the login page when a webview is detected.

## Step 1: Create the Google Cloud project

1. Open https://console.cloud.google.com and sign in with the Google account that should own the app (use a team/shared account, not a personal one, if others will maintain it).
2. Top bar project picker, New Project. Name: `ResolveAI` (the project ID is generated; it cannot be changed later). Create, then select it.

## Step 2: Configure the Google Auth Platform

Menu: APIs & Services, OAuth consent screen (this opens "Google Auth Platform"), then Get started.

1. **App information:** App name `ResolveAI`, User support email (your email).
2. **Audience:** choose **External** (anyone with a Google account). Internal only works for a Google Workspace organization.
3. **Contact information:** developer email for Google notices.
4. Agree to the user data policy and Create.

Then fill in the tabs:

- **Branding:** logo (optional, 120x120 PNG; adding a logo can trigger brand verification), Application home page, Privacy policy link and Terms link (needed to publish; placeholder pages are fine while testing), and **Authorized domains** (add your production domain, for example `example.com`; not needed for localhost).
- **Audience:** keep Publishing status **Testing** while developing and add your Google addresses under **Test users** (up to 100). Only test users can sign in while in Testing. Move to **In production** when you launch; with only `openid email profile` there is no scope review. A "Google hasn't verified this app" screen can appear until branding is verified; it is skippable for test users.
- **Data access:** first enable the Gmail API (APIs & Services > Library > Gmail API > Enable). Then Add or remove scopes: select `openid`, `.../auth/userinfo.email`, `.../auth/userinfo.profile`, and the Gmail scopes `https://www.googleapis.com/auth/gmail.send` and `https://www.googleapis.com/auth/gmail.readonly` (if the picker does not list them, use "Manually add scopes" and paste the two URLs). Update, Save. Do not add `gmail.modify`.

Important: in **Testing** mode, Google expires refresh tokens after 7 days, so users must sign in again (use `?reconnect=1`, or just sign out and in) about weekly for Gmail to keep working. `gmail.readonly` is a restricted scope and `gmail.send` is sensitive: before real users can sign in, the app needs OAuth verification and, for the restricted scope, a security assessment. Until then only the listed test users (up to 100) can sign in at all, and they see an unverified-app warning. Plan that review early.

## Step 3: Create the OAuth client

Menu: Google Auth Platform, Clients, Create client.

1. Application type: **Web application**. Name: `ResolveAI web (local)`.
2. **Authorized JavaScript origins:** not required for this flow; leave empty (add `http://localhost:3000` only if you later use Google's JS library).
3. **Authorized redirect URIs** (exact match, including scheme, host, port, path and trailing slash):
   - `http://localhost:3000/api/auth/google/login/callback/` (frontend dev server proxying `/api`, the recommended local path)
   - `http://localhost:8000/api/auth/google/login/callback/` (backend container hit directly)
   - Production later: `https://app.yourdomain.com/api/auth/google/login/callback/`
4. Create. Copy the **Client ID** and **Client secret** (the secret can be viewed again under the client; treat it as a password).

Rules Google enforces: production redirect URIs must be `https`; `http` is allowed only for `localhost`; no raw IP addresses (use `localhost`), no `.local`/private suffixes, no wildcards. Create a second client (`ResolveAI web (prod)`) for production so secrets and URIs stay separate. Changes can take a few minutes to apply (occasionally up to hours).

## Step 4: Put the values in `backend/.env`

```
RESOLVE_AI_GOOGLE_CLIENT_ID=<client id>.apps.googleusercontent.com
RESOLVE_AI_GOOGLE_CLIENT_SECRET=<client secret>
# Public origin the browser uses to reach /api (must match the redirect URI host)
RESOLVE_AI_PUBLIC_API_URL=http://localhost:3000
```

These variables are added to `.env.example` and `config/settings.py` when feature 1 is built. Never commit `.env` or the secret.

## Step 5: Gmail push notifications (optional, Pub/Sub)

Without push, new customer mail is read only when an agent presses "Sync latest mails". To receive it as it arrives:

1. Enable the **Cloud Pub/Sub API** in the same project.
2. Create a topic, for example `gmail-inbound`. Give `gmail-api-push@system.gserviceaccount.com` the **Pub/Sub Publisher** role on that topic (topic > Permissions).
3. Create a **push subscription** on the topic. Endpoint URL: `https://<your public API origin>/api/email/gmail/push/` (it must be reachable from the internet; use a tunnel such as ngrok in development). Enable **authentication** and choose a service account (create one such as `gmail-push@<project>.iam.gserviceaccount.com`); set the **audience** to the same endpoint URL.
4. Put these in `backend/.env`, then run `docker compose up -d api`:
   ```
   RESOLVE_AI_GMAIL_PUBSUB_TOPIC=projects/<project-id>/topics/gmail-inbound
   RESOLVE_AI_PUBSUB_PUSH_AUDIENCE=https://<your public API origin>/api/email/gmail/push/
   RESOLVE_AI_PUBSUB_PUSH_SERVICE_ACCOUNT=gmail-push@<project>.iam.gserviceaccount.com
   ```
5. Sign in again (or `?reconnect=1`) so the watch is registered; it is renewed daily by Celery beat. Leaving the three variables empty turns push off. A Celery worker (and beat for renewals) must be running.

## Step 6: Verify

1. Start the stack (`docker compose up --build`).
2. Open `http://localhost:3000/api/auth/google/start/` (or the backend URL). You should land on Google's account chooser, then return to the app.
3. Expect `Error 400: redirect_uri_mismatch` if the URI in Google and the one the backend sends differ by even a character.

## Troubleshooting

| Symptom | Likely cause and fix |
| --- | --- |
| `redirect_uri_mismatch` | The redirect URI in the client does not exactly match the one sent. Compare scheme, `localhost` vs `127.0.0.1`, port, trailing slash; wait a few minutes after editing. |
| `access_denied` / "app is being tested" | Your Google address is not in Test users, or the app is in Testing and you used another account. |
| "Google hasn't verified this app" | Normal in Testing/unverified branding. Continue (Advanced) as a test user, or complete branding verification before launch. |
| `invalid_client` / `unauthorized_client` | Wrong client ID/secret, or the secret was regenerated. |
| `disallowed_useragent` | Opened inside an embedded webview. Open in a normal browser. |
| Returns to login with an error and no session | State cookie missing: different host between start and callback (for example start on `localhost:8000`, callback on `localhost:3000`), cookies disabled, or `Secure` cookie on plain HTTP. Use one origin end to end. |
| Works locally, fails in production | Production client missing the `https` redirect URI, `RESOLVE_AI_PUBLIC_API_URL` not set to the public https origin, proxy not forwarding `X-Forwarded-Proto` (the backend would build an `http` URI), or secure cookies not enabled. |
| Token errors after a long pause | Codes are single-use and expire in minutes; the user must restart sign-in. |

## Security notes

- The client secret stays on the server; the browser only sees redirects.
- State and the PKCE verifier are random per attempt and kept in the server-side session bound to the browser; allauth validates them.
- The session is created only after the ID token is verified and `email_verified` is true. Accounts are keyed on the Google `sub`, never merged by email.
- Add the Google client ID/secret to your secret manager for production; rotate the secret from the console if it leaks.
