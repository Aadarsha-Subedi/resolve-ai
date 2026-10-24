# Project.MD: ResolveAI Backend v1 Feature Map

2026-10-20

## Overview

ResolveAI is a multi-tenant support desk. Customers submit tickets through a public workspace portal; workspace members answer them by email (Gmail API) from a shared ticket view. **v1 is backend only and has no AI or RAG features** (no Gemini, no full-text search, no text extraction). The AI layer is a later phase and is listed at the end.

Source documents: `docs/ResolveAI_LLD.md` (design), `CLAUDE.md` (rules), `DECISION.md` (decision log), `FLOW.md` (code paths), `postman/` (API collection). Anything decided here is also in `DECISION.md`.

### Stack

Django 6.1 + DRF, PostgreSQL, Redis, Celery, `uv`, Python 3.14; Docker for dev and prod (`Dockerfile.dev`, `Dockerfile.prod`). Google OAuth through django-allauth with server-side Django sessions; Gmail API.

### Conventions used everywhere

- Workspace is the tenant. Every workspace-owned query is filtered by an authorized active membership; non-members get **404**, never 403.
- UUIDv7 primary keys, UTC timestamps, absolute imports, business logic in `services/`, thin views.
- Responses use the common envelope `{success, status_code, message, data, meta}`; errors carry a stable `code`. Lists use page size 25 (maximum 100). Unknown request fields are rejected.
- Authorization: RBAC permission codes (fixed role presets, `OWNER` and `MEMBER`) plus fixed ABAC rules in code. Both enforced in services and DRF permissions.
- Every feature ships with: models and migrations, services, serializers, views and URLs, constants, tests (including negative authorization tests), a Postman folder, and updates to FLOW.md, DECISION.md and README.

### Confirmed decisions (owner, 2026-10-16 to 2026-10-20)

- Google-only sign-in; "remember me", per-device session list, revoke one device, log out of all devices.
- One owner per workspace; join link grants membership directly; ownership transfer; fixed role presets (no per-member permission customization).
- Ticket statuses OPEN, IN_PROGRESS, PENDING, RESOLVED, CLOSED; any member moves between them, only the owner reopens CLOSED. Fixed ticket categories: Billing, Technical, Account, Feature request, General, Other.
- Public portal per workspace (on by default, owner toggle); name optional, email, subject, description; no attachments; rate limit + honeypot, no CAPTCHA. Customer follow-up is by email only; no customer access token.
- Knowledge base: in-app articles plus PDF/DOCX/MD/TXT uploads (read with pdfplumber and python-docx in the background and searched together with the articles, see Feature 8); 50 MB per workspace; simple filter by title, status, category (no full-text search in v1). Default categories: General, Getting started, Billing, Troubleshooting, FAQ; users can add, rename, delete.
- Gmail: one connection per user; agents send from their own mailbox (no connection, no send); portal confirmation is sent from the owner's mailbox (skipped if none). Inbound via Pub/Sub push plus a "Sync latest mails" button, no polling; matched by headers; unmatched mail goes to a review list.
- Dashboard: open and urgent counts, volume over time, recently updated, waiting for reply (last public message is from the customer), recent activity. No AI metrics.
- Account deletion blocked while owning a workspace; 7-day grace. Workspace deletion by owner, purged after 7 days. Audit log: owner-only list, no export.
- Tickets have one optional assignee (an active member), set from the ticket page; see Feature 5.

## Feature map and build order

| # | Feature | Depends on | Status |
| --- | --- | --- | --- |
| 0 | Foundation: `common` app, config, Docker, Postman, docs | none | Done |
| 1 | Accounts and sessions (`accounts`) | 0 | Done, breakdown below |
| 2 | Audit log (`audit`) | all other features | Done (built last, as decided) |
| 3 | Workspaces and membership (`workspaces`) | 1 | Done, details below |
| 4 | Knowledge base (`knowledge`) | 3 | Done, details below |
| 5 | Tickets and public portal (`tickets`) | 3 | Done, details below |
| 6 | Gmail connection and email (`email_integration`) | 1, 3, 5 | Done, details below |
| 7 | Dashboard (served by the `audit` app) | 3, 5 | Done, details below |

Build order is 1, 3, 4, 5, 6, 7, then 2. The audit log (feature 2) is built last so it is written once against the finished product instead of being edited by every feature (owner decision, 2026-10-20). Until then each feature records what it does through its own hook (for example `accounts.services.hooks.account_event`), and the dashboard's "recent activity" uses `TicketEvent` only. Notes: feature 4 comes before 5 only because it is simpler; they are independent and may swap. Feature 6 splits into 6a (connect/disconnect Gmail), 6b (send replies and confirmations) and 6c (inbound Pub/Sub, sync button, review list).

## Feature 1: Accounts and sessions (granular breakdown)

**Purpose:** let people sign in with Google, keep a server-side session, manage their profile and devices, and delete their account safely. Built on **django-allauth** (Google provider, `usersessions`); our code covers the user model, rules, API envelope and deletion.

### 1.1 What allauth does and what we write

| Concern | allauth provides | We write |
| --- | --- | --- |
| Google OAuth (code flow, PKCE, state, token exchange, ID token check, account linking by Google `sub`) | `allauth.socialaccount` + Google provider; `SocialAccount.uid` is the `sub` | Settings, a social-account adapter (rules, redirects) |
| Email records | `EmailAddress` (verified by Google) | Nothing |
| Device sessions (list, delete one, delete all) | `allauth.usersessions` (`UserSession` with user agent, IP, timestamps) | JSON endpoints in our envelope, device label parsing |
| Remember me | `ACCOUNT_SESSION_REMEMBER` / session expiry | Choice passed through our start endpoint |
| Not used | Password, signup, reset, email-change flows and allauth's HTML pages, headless API, MFA | We expose only the Google provider URLs |

Hand-written OAuth code is not needed. Pieces marked "verify" are checked against the installed allauth version when building.

### 1.2 Models (`accounts/models/`)

- `User` (custom `AUTH_USER_MODEL`, must exist before the first migration of any app): `id` UUIDv7, `email` (normalized), `display_name`, `avatar_url` (Google picture URL, no uploads in v1), `is_active`, `deletion_requested_at` (nullable), `last_login`, `created_at`, `updated_at`. No password (unusable) and no username. The Google `sub` is **not** duplicated on `User`; it is `SocialAccount.uid`, read through `accounts.services.identity.get_google_subject(user)` (used later to check Gmail connections). Managers: `User.objects` (all rows) and `User.visible` (hides accounts pending deletion).
- Device sessions use allauth's `UserSession`; no model of our own unless a needed field is missing (verify: last-activity field, `remember_me` flag; if absent, a small `accounts.SessionMeta` one-to-one is added).

### 1.3 Google sign-in flow

- `GET /api/auth/google/start/?remember=0|1&next=/path`: our thin view validates `next` (same-site path only), stores `remember` in the session, and redirects to allauth's Google login URL (`SOCIALACCOUNT_LOGIN_ON_GET = True` so no intermediate page).
- allauth redirects to Google (PKCE on, scopes `openid email profile`, `prompt=select_account`), receives the `GET` callback at `/api/auth/google/login/callback/`, checks state, exchanges the code with the client secret, validates the ID token and logs the user in. Only the Google provider URLs are mounted; allauth's account/HTML URLs are not.
- Our `SocialAccountAdapter`: rejects unverified emails and inactive users; blocks linking by email to an existing account with a different `sub`; fills `display_name` and `avatar_url` on first login and refreshes them on later logins; on success applies remember-me expiry and redirects to the app (`/app`); on any authentication error redirects to `/login?google_error=<code>` (never shows allauth's HTML error page).
- First login creates the user (`SOCIALACCOUNT_AUTO_SIGNUP = True`, no signup form). The session key is rotated on login; the browser receives only the session cookie, never Google tokens (`SOCIALACCOUNT_STORE_TOKENS = False`).
- Logging in during the deletion grace period cancels the deletion.
- Why a redirect flow and not Google's button/popup: see `docs/GOOGLE_OAUTH_SETUP.md` (browser compatibility lessons from the previous project).

### 1.4 Sessions

- Django `cached_db` sessions; `allauth.usersessions` records a row per session (middleware `UserSessionsMiddleware`). Remember me gives the 30-day sliding lifetime, otherwise 14 days.
- Our endpoints list sessions with a device label (browser + OS parsed from the user agent), last active, created, and which one is current; delete one (the current session is ended through logout); log out of all devices. IP is stored by allauth but never returned by the API.
- Revoked sessions are rejected on the next request (they no longer exist). Daily Celery task clears expired sessions.

### 1.5 Profile (`profile_service.py`)

- Read own profile; update `display_name` (trimmed, bounded length). Email and avatar come from Google.

### 1.6 Account deletion (`deletion_service.py`)

- Request deletion: allowed only if no ownership blockers (an `ownership_checks` registry that workspaces populates in feature 3); sets `deletion_requested_at`, ends all sessions, purge after 7 days.
- Cancel by signing in again within the grace period.
- Daily task `purge_deleted_accounts` hard-deletes after the grace period (historical ticket messages keep their author as a removed user).

### 1.7 Endpoints (under `/api/`)

| Method | Path | Owner | Purpose |
| --- | --- | --- | --- |
| GET | `/csrf/` | ours | Set the CSRF cookie |
| GET | `/auth/google/start/?remember=0\|1&next=` | ours | Begin sign-in (redirect) |
| GET | `/auth/google/login/callback/` | allauth | Google redirect target; ends in a redirect to the app |
| POST | `/auth/logout/` | ours | End the current session |
| POST | `/auth/logout-all/` | ours | End every session of the user |
| GET | `/auth/sessions/` | ours | List own sessions (marks the current one) |
| DELETE | `/auth/sessions/{id}/` | ours | Revoke one device |
| GET | `/me/` | ours | Own profile |
| PATCH | `/me/` | ours | Update `display_name` |
| DELETE | `/me/` | ours | Request account deletion |

Throttling and rate limits (checked against allauth 65.20.0):

- allauth's own limits (`ACCOUNT_RATE_LIMITS`: login 30/min per IP, signup 20/min per IP, password reset, email confirmation, and so on) apply only to its account views. The Google provider and `usersessions` code have **no rate limiting**. We do not expose allauth's account views, so those defaults are left untouched and unused.
- So the Google endpoints get our own throttling. `/auth/google/start/` is a thin DRF view using `common.throttling.scoped` (`AnonThrottle` plus `AuthScopedThrottle` with scope `google`, 20/min per IP; relaxed in dev and tests). The callback is mounted through a thin wrapper view that applies the same throttles and then hands the request to allauth's callback view, so the limit is enforced with the same cache/Redis counters as the rest of the API. A throttled or failed request ends as a redirect to `/login?google_error=rate_limited` (or `google_failed`), never a JSON error or allauth's HTML page.
- Natural limits that help: the callback needs a valid single-use `state` held in the caller's own session and a single-use Google code; unauthenticated callbacks with no matching state are rejected early.
- JSON endpoints (`/me/`, `/auth/sessions/`, logout, logout-all, delete) use the default user/anon throttles from settings, plus a stricter `account_delete` scope for `DELETE /me/`.
- Tests: exceeding the `google` rate redirects with `rate_limited`; the limit is per IP; throttle counters are cleared between tests.

### 1.8 Supporting pieces

- Dependencies: `django-allauth[socialaccount]`.
- Settings: `AUTH_USER_MODEL = "accounts.User"`; apps `allauth`, `allauth.account`, `allauth.socialaccount`, `allauth.socialaccount.providers.google`, `allauth.usersessions`; `allauth.account.middleware.AccountMiddleware` and the usersessions middleware; `SOCIALACCOUNT_PROVIDERS["google"]` with `APPS` from env (`GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`), PKCE on; `ACCOUNT_USER_MODEL_USERNAME_FIELD = None`, `ACCOUNT_EMAIL_VERIFICATION = "none"` (Google verifies), `SOCIALACCOUNT_AUTO_SIGNUP = True`, `SOCIALACCOUNT_LOGIN_ON_GET = True`, `SOCIALACCOUNT_STORE_TOKENS = False`, adapter classes, `ACCOUNT_DELETION_GRACE_DAYS = 7`, `PUBLIC_API_URL`, the `google` (20/min) and `account_delete` throttle rates, beat schedule entries.
- New env vars in `.env.example`: `RESOLVE_AI_GOOGLE_CLIENT_ID`, `RESOLVE_AI_GOOGLE_CLIENT_SECRET`, `RESOLVE_AI_PUBLIC_API_URL`.
- Constants in `accounts/constants/` (messages, error codes, cache keys, session settings, task names). Views: an authenticated base using the common envelope.
- Hooks for later features: `ownership_checks` registry (workspaces) and an `accounts.services.hooks` event that audit (feature 2, built last) subscribes to.
- Postman: `Auth` and `Account` folders; `csrfToken` captured from the CSRF cookie.
- Tests: first login vs repeat login (mocked Google), unverified email rejected, email held by another `sub` rejected, inactive user rejected, state mismatch / failed exchange redirects to `/login?google_error=`, open-redirect protection on `next`, session rotation, remember-me expiry, list/revoke one/revoke all, revoked session rejected, deletion blocked by an ownership check, deletion grace and cancel by login, purge task, CSRF on POST endpoints, throttling, no token or secret in responses or logs, allauth password/signup URLs not reachable.

### 1.9 Out of scope for feature 1

Passwords, email verification flows, avatar upload, other login providers, MFA, allauth headless API and HTML pages, login lockout (no passwords to guess), Gmail scopes (separate consent in feature 6), admin panel customization.

## Features 2 to 7 (outline)

### Feature 2: Audit log (`audit`), built last (owner decision of 2026-10-20)

`AuditEvent` (UUIDv7, `workspace` nullable, `actor_user` plus an `actor_name` snapshot, `action`, `target_type`/`target_id`, sanitised flat `metadata`, `created_at`) and `audit.services.recorder.record(...)`, which never raises: a failing audit write is logged and the audited action carries on. Rows are append-only (saving an existing row raises) and have no API to change or delete them.

- **How features feed it:** each feature already emits a hook signal (`accounts`, `workspaces`, `knowledge`, `tickets`, `email_integration`). `audit/signals.py` subscribes to all of them, so feature code does not call the audit app. Which actions are kept, and what each points at, is one table: `audit/constants/actions.py`. A new feature registers its sensitive actions there; an unregistered action is ignored.
- **Recorded:** workspace created/updated/deleted/logo changed; member joined/left/removed; ownership transferred; join link created/revoked; invitation created/revoked/accepted/declined; every knowledge-base article, category and upload action; ticket created/updated/status changed (old and new status, so closing and reopening show); account-level (no workspace, kept for security reviews, not in the workspace API): account deletion requested/cancelled/completed, log out everywhere, session revoked, Gmail connected/reauthorisation needed/disconnected. **Not recorded:** ticket replies and notes (the ticket's own history), logins/logouts/profile edits (noise), `workspace.purged` (its rows are deleted with the workspace).
- **Never stored:** tokens, raw join tokens, message or article text, snippets, cookies/sessions, passwords or keys (dropped by key name), email addresses (masked if one slips in), nested objects; strings are capped at 200 characters and a whole metadata blob at 2,000 (else replaced by `{"truncated": true}`).
- **Endpoint:** `GET /api/workspaces/{id}/audit/`, owner only (`audit.view` is held by OWNER only: members 403, non-members 404), newest first, paginated (25, max 100). Filters: `action`, `action_prefix`, `actor`, `target_type`, `target_id`, `created_from`, `created_to`. No export, no write methods. Reading the log is not itself audited.
- **Lifetime:** a workspace's rows are purged with the workspace (7 days after deletion). They survive removal of members and deletion of the actor's account (the name snapshot stays). No retention limit otherwise in v1.

### Feature 3: Workspaces and membership (`workspaces`), built

Models: `Workspace` (UUIDv7, name, immutable unique slug, `logo_key`, `portal_enabled`, soft delete), `WorkspaceMembership` (OWNER/MEMBER, ACTIVE/REMOVED; database constraints allow one membership per user and one active owner per workspace), `WorkspaceJoinLink` (SHA-256 token hash, `expires_at`, `revoked_at`; one unrevoked link per workspace), `WorkspaceInvitation` (address as typed plus a canonical mailbox key, `expires_at`, `accepted_at`, `closed_at`).

Rules (owner answers of 2026-10-20):
- **Join link:** direct membership, expires after **1 hour** by default; the owner may choose 1 hour, 1 day or 7 days. Creating a link rotates (revokes) the previous one. The raw token and URL (`FRONTEND_URL/join/<token>`) are shown once; status calls return metadata only. Redemption is limited per IP (`join_link` scope); unknown, expired, revoked and deleted-workspace links return the same 404.
- **Invitations:** the owner invites one or several Google accounts (max 20 per request, 7-day expiry, single use). A person sees and accepts invitations for the mailbox they signed in with; acceptance is an explicit step. Gmail addresses are compared by mailbox (`common.email.utils.canonical_email_key`: dots and `+tags` ignored, `googlemail.com` = `gmail.com`), other domains only lower-cased. `x.y@gmail.com` is mailbox `xy`, while `x+y@gmail.com` is mailbox `x`. Each new invitation is also emailed to the invitee from the inviter's own Gmail by a Celery task (2026-10-21, see Feature 6); with no connected Gmail, or when Gmail fails, nothing is sent (`notified_at` stays empty), creation never fails, and the invitee still finds the invitation in the app.
- **Roles:** fixed presets in `workspaces/constants/permissions.py` (`OWNER` has every code, `MEMBER` can view the workspace and the member list). Non-members and removed members get 404; members lacking a permission get 403. `WorkspaceAccessPolicy` answers the boolean questions.
- **Ownership transfer** is one transaction (old owner demoted first, then the target promoted). The owner cannot leave or be removed. Removal keeps the membership row (history) and revokes access; a removed person can come back through a link or an invitation as a MEMBER.
- **Deletion:** the owner soft-deletes a workspace; it vanishes for everyone at once and a daily task (`workspaces.purge_deleted_workspaces`) hard-deletes it, and its logo object, after 7 days. `account_ownership_blocker` is registered with the account-deletion check, so an owner must transfer or delete first.
- **Logo:** direct-to-R2 upload with a signed PUT (`logo/upload-url/`, then `PUT logo/` to confirm; the server verifies the object, type and size, 2 MB, PNG/JPEG/WebP). Needs R2 configured.
- Audit: every action calls `workspaces.services.hooks.emit`, a signal the audit app subscribes to later.

Endpoints (under `/api/`): `workspaces/` (GET list, POST create), `workspaces/{id}/` (GET, PATCH name and portal_enabled, DELETE), `workspaces/{id}/transfer-ownership/`, `workspaces/{id}/members/`, `workspaces/{id}/members/{user_id}/` (DELETE), `workspaces/{id}/leave/`, `workspaces/{id}/join-link/` (GET, POST, DELETE), `join-links/redeem/`, `workspaces/{id}/invitations/` (GET, POST), `workspaces/{id}/invitations/{id}/` (DELETE), `invitations/` (mine), `invitations/{id}/accept/`, `invitations/{id}/decline/`, `workspaces/{id}/logo/upload-url/`, `workspaces/{id}/logo/` (PUT, DELETE).

### Feature 4: Knowledge base (`knowledge`), built

Models: `KnowledgeArticle` (draft/published/archived; metadata in the database, the Markdown body is an object in R2), `KnowledgeCategory` (per workspace, unique slug), `KnowledgeArticleCategory` (many-to-many), `KnowledgeUpload` (PDF/TXT metadata; PENDING until the browser upload is confirmed, then READY). `Workspace.storage_used_bytes` holds the quota counter.

Rules (owner answers D5, D6 and the defaults of 2026-10-20):
- **Storage:** article Markdown lives in `KnowledgeArticle.content` (since 2026-10-22); uploaded files go to the same R2 bucket as the logo, one prefix per workspace: `workspaces/{id}/knowledge/uploads/{upload_id}.pdf|txt`. Keys never contain user-supplied names; the display filename is kept in the database. Articles and uploads (not the logo) all count toward the 50 MB per-workspace quota.
- **Quota:** one conditional `UPDATE` reserves space (articles on save, uploads when the upload URL is issued) so concurrent writers cannot overshoot; it answers 413 `storage_quota_exceeded` when full. Deleting or shrinking frees space. Uploads never confirmed within 1 hour are removed by the hourly task `knowledge.release_stale_uploads`.
- **Articles:** title up to 200 characters, body up to 200 KB (UTF-8 bytes), up to 10 categories. Status changes go through `publish`, `unpublish` (back to draft) and `archive`; PATCH cannot change status. ABAC rule: archived articles are read-only until moved back to draft. Delete is permanent and removes the stored object. A storage failure rolls the row and the quota change back.
- **Uploads:** every file is filed under one category of its workspace (`category_id` required when asking for the upload URL; a deleted category leaves the file uncategorized; `GET uploads/?category=&filename=`). PDF, DOCX, MD or TXT (no legacy .doc), 1 byte to 10 MB, signed direct upload then confirm. Confirm checks exact size and content type (PDFs must start with `%PDF-`, DOCX must be a zip with the Word parts) and discards anything else; it then queues reading the file (`index_status`: pending, indexing, indexed, failed). Downloads are signed URLs that force a download, valid 5 minutes. Text extraction and indexing: see Feature 8.
- **Filters:** `?title=` (contains), `?status=`, `?category=<id>`, `?ordering=` (title, created_at, updated_at, published_at), plus limit/offset. Passage search for tickets and chat is a separate endpoint (Feature 8); the article list has no full-text filter.
- **Categories:** defaults General, Getting started, Billing, Troubleshooting, FAQ are created with each workspace (and by a data migration for existing ones). Owner and members may add, rename and delete them; names are unique per workspace (case-insensitive through the slug); deleting a category only unlinks it.
- **Access:** both roles may view and manage the knowledge base (`knowledge.view`, `knowledge.manage`); non-members get 404.
- When a workspace is purged, its stored article and upload objects are deleted. Audit hook: `knowledge.services.hooks.knowledge_event`.
- Known limit: no versioning. An article save overwrites the stored object, so a crash between the database commit and the storage write is the only way the two can disagree (the write happens last inside the transaction so a failure undoes the rows).

Endpoints (under `/api/workspaces/{workspace_id}/knowledge/`): `articles/` (GET, POST), `articles/{id}/` (GET, PATCH, DELETE), `articles/{id}/publish|unpublish|archive/` (POST), `categories/` (GET, POST), `categories/{id}/` (PATCH, DELETE), `uploads/` (GET), `uploads/upload-url/` (POST), `uploads/{id}/confirm/` (POST), `uploads/{id}/download/` (GET), `uploads/{id}/` (DELETE), `storage/` (GET).

### Feature 5: Tickets and public portal (`tickets`), built

Models: `Ticket` (per-workspace number, subject, description, customer name/email, status, priority, fixed category, `created_via` PORTAL/AGENT/EMAIL, resolved/closed/last-activity timestamps, `last_customer_message_at` and `last_agent_reply_at`, `confirmation_pending`), `TicketMessage` (public or internal, author type, direction, delivery status, and email correlation fields that feature 6 fills), `TicketEvent` (history without message text). `Workspace.last_ticket_number` is the counter behind the numbers.

Rules (owner approved the proposed defaults, 2026-10-20):
- **Numbers:** per workspace from 1 (`#1`), allocated with an `UPDATE ... SET n = n + 1` on the workspace row inside the creating transaction, so concurrent creators queue, there are no duplicates, and a rollback gives the number back.
- **Categories (fixed):** billing, technical, account, feature_request, general (default), other. **Priority:** low, medium (default), high, urgent; customers cannot set it. **Statuses:** open, in_progress, pending, resolved, closed. No ticket deletion. **Assignment (2026-10-21):** a nullable `assignee` (any ACTIVE member of the workspace, validated on assign, else 400 `assignee_invalid`); `POST tickets/{id}/assignee/` with `{"assignee": <user id> | null}`; permission `tickets.assign` (owner and member); an `assignee_changed` history event (old and new as `{id, display_name}`) and the audited action `ticket.assignee_changed` (ids only). Re-assigning the current assignee changes nothing. When a member leaves or is removed, their OPEN / IN_PROGRESS / PENDING tickets are unassigned (system event, no actor, `reason`); RESOLVED and CLOSED tickets keep the assignee as history. List filter `assignee=<user id>|me|unassigned`. The assignee is returned as `{id, display_name}` (or null) in the list, detail and overview.
- **ABAC (`tickets/policies.py`):** any member changes status freely, but only the owner moves a ticket out of CLOSED (403 `owner_only_reopen`). On a CLOSED ticket members cannot edit subject, description, customer fields, category or priority, nor change the assignee (403 `ticket_closed`); the owner can. Nobody can add a public reply to a CLOSED ticket (reopen first); internal notes are still allowed.
- **Messages:** an internal note (never customer-visible) or a public reply, up to 20,000 plain-text characters. A public reply is stored first with delivery status QUEUED; feature 6 sends it from the agent's own Gmail. Messages cannot be edited or deleted. Replies do not change status; "waiting for reply" is computed (last customer message newer than the last agent reply, and the `waiting_for_reply` list filter). The customer's description is stored as the first public message.
- **History:** `TicketEvent` rows for created, status/priority/category/details changed, public reply added, internal note added (message ids, not bodies).
- **Portal (no login, no CSRF):** `GET /api/portal/{slug}/` (name, slug, logo only) and `POST /api/portal/{slug}/tickets/` (email required; name, subject, description, optional category). Unknown slug, deleted workspace and disabled portal all answer the same 404. Protection: per-IP limit (`portal_ticket` scope), at most 5 tickets per customer email per workspace per hour (429 `portal_email_rate_limited`), and a hidden `website` field that, when filled, returns a normal-looking success without creating anything. The response carries only the ticket number. No customer token or ticket page; follow-up is by email (feature 6). Portal tickets are flagged `confirmation_pending` until feature 6 sends the confirmation from the owner's mailbox.
- **Access:** owner and members see every ticket of the workspace; non-members get 404. Audit hook: `tickets.services.hooks.ticket_signal`.
- **One call per screen (owner decision, 2026-10-20):** the frontend should not fan out several requests to draw one screen. `GET .../tickets/{id}/overview/` returns the ticket detail, `viewer` (role and permission codes), `messages`, `events`, `meta` totals and an `email` block (the viewer's own Gmail status) together; `?messages_limit=` and `?events_limit=` (1-100, default 50) return the newest items in order, and older ones come from the paginated `messages/` and `events/` endpoints. Other apps contribute blocks through `tickets.services.overview_service.register_extra` (the Gmail block is registered by `email_integration`), so `tickets` never imports them. The separate endpoints stay for refreshes and other clients. Later screens follow the same rule (the dashboard is one endpoint by design).

Endpoints: `/api/workspaces/{workspace_id}/tickets/` (GET list with filters `status`, `priority`, `category`, `created_from`, `created_to`, `q`, `waiting_for_reply`, `assignee`, `ordering`; POST create), `tickets/{id}/` (GET, PATCH), `tickets/{id}/assignee/` (POST), `tickets/{id}/overview/` (GET: the whole ticket page in one call, see below), `tickets/{id}/status/` (POST), `tickets/{id}/messages/` (GET, POST), `tickets/{id}/events/` (GET), and the public `/api/portal/{slug}/` and `/api/portal/{slug}/tickets/`.

### Feature 6: Gmail connection and email (`email_integration`), built

**One sign-in flow.** Owner decision (2026-10-20): there is no separate "Connect Gmail" flow. Google sign-in requests `openid email profile` plus `gmail.send` and `gmail.readonly` with `access_type=offline`. After login, `email_integration.signals.record_gmail_grant` (allauth's `user_logged_in`, which carries the `sociallogin`) reads which scopes Google really granted (`tokeninfo`), and stores the refresh token **encrypted** (`common.crypto`) in `GmailConnection` (one per user). allauth's own token storage stays off. Statuses: `connected`, `not_connected` (Gmail permission declined, or Google sent no refresh token), `reauth_required` (token revoked or expired; Testing-mode tokens last 7 days), `disconnected`. Declining Gmail never blocks sign-in. Google sends the refresh token only on first consent, so `GET /api/auth/google/start/?reconnect=1` forces `prompt=consent`. No passwords or app passwords are ever used.

- **Client:** `clients/base.py::GmailClient` (interface), `rest.py::RestGmailClient` (plain HTTPS with `requests`, refreshing access tokens as needed), `fake.py::FakeGmailClient` (tests). `clients.get_gmail_client(connection)` is the single factory.
- **Sending (6b):** a public reply is stored first (`queued`), then a Celery task emails it from **the agent's own mailbox** (`From` = their Gmail, `To` = the customer, `Subject` = `Re: <subject> [#n]`, `In-Reply-To`/`References` from the ticket's known Message-IDs, Gmail `threadId` reused for that mailbox). After sending, the sent message is read back to store the Message-ID Gmail actually used. Internal notes are never emailed. Outcomes: `sent`, or `failed` with `delivery_error` (`gmail_not_connected`, `gmail_reauth_required`, `gmail_rejected`, `gmail_unavailable`) and an `email_delivery_failed` ticket event; temporary Gmail errors retry 3 times first. Failed replies can be re-queued (`.../messages/{id}/resend/`). Header values are stripped of line breaks.
- **Portal confirmation:** after a portal ticket is created, the **owner's** mailbox sends "We received your request #n" (skipped if the owner has no connected Gmail). It is stored as a `system` message so the customer's reply threads onto the ticket.
- **Invitation email (2026-10-21):** creating invitations queues `email_integration.send_invitation_email` per new invitation (through the `workspaces.services.hooks.invitations_created` signal, after commit). It sends a short plain-text mail from the inviter's Gmail: who invited them, the workspace name and a link to `RESOLVE_AI_FRONTEND_URL` + `/app/invitations`. No token is in the mail or in logs (the invitation is matched by the invitee's signed-in Google account). A missing or broken Gmail connection skips the mail and is logged by invitation id only.
- **Inbound (6c):** mail arrives through Pub/Sub push (`POST /api/email/gmail/push/`, Google-signed JWT checked against the configured audience and service account) and the "Sync latest mails" button (`POST /api/email/gmail/sync/`, newest 30 inbox messages only). No polling. Push uses a stored Gmail history checkpoint; the first run only records the starting point, so **nothing from before the connection is imported**. Watches are registered at connect and renewed daily.
- **Matching:** by headers only (`In-Reply-To`/`References` against stored Message-IDs of tickets in the agent's workspaces), never by subject. The sender must also be the ticket's customer (Gmail dot/plus spellings count as the same mailbox), otherwise anyone who learned a Message-ID could write into a ticket. A match stores the reply as a plain-text inbound message with the quoted history stripped, updates `waiting_for_reply`, and records a `customer_reply_received` event. Deduplicated by Message-ID.
- **Privacy:** mail that does not match is stored only if it comes from the address of a known customer (a ticket in one of the agent's workspaces); it goes to the review list as sender, subject and a 300-character snippet (newest 30 per user, kept 30 days). Everything else in the mailbox is ignored and not stored. An agent can attach a review item to a ticket (its text is then fetched from Gmail) or dismiss it.
- **For the AI phase:** a ticket's history for an LLM is its `TicketMessage` rows (ordered, only that ticket, both directions), not a Gmail thread. Gmail `threadId` is per mailbox and is kept only for correlation.
- **Disconnect:** `DELETE /api/email/gmail/` stops the watch, revokes the grant at Google and deletes our copy.

New env vars: `RESOLVE_AI_GMAIL_PUBSUB_TOPIC`, `RESOLVE_AI_PUBSUB_PUSH_AUDIENCE`, `RESOLVE_AI_PUBSUB_PUSH_SERVICE_ACCOUNT` (all empty = push off; the sync button still works). Google Cloud setup: `docs/GOOGLE_OAUTH_SETUP.md`.

### Feature 7: Dashboard (lives in the `audit` app)

One read endpoint, `GET /api/workspaces/{workspace_id}/dashboard/`, implemented inside the `audit` app (`audit/views/dashboard.py`, `audit/services/dashboard_*.py`; owner decision, there is no separate `dashboard` app), returns everything the dashboard screen shows (owner decision: one call per screen). Exact JSON shape: [docs/DASHBOARD_API.md](docs/DASHBOARD_API.md).

- **Definitions:** *active* = open, in_progress or pending. *Urgent* = active with priority urgent; *high* is counted separately (high is not folded into urgent). *Waiting for reply* = active ticket whose last customer message is later than the last agent reply (or that has no agent reply). *Resolved* is counted by `resolved_at`, which is set on the first entry into resolved or closed and cleared only when the ticket goes back to an active status. No SLA or response-time claims.
- **Period:** `period=7d|30d|90d` (default 30d; the last N local days ending today) or `from` and `to` (dates, inclusive, at most 366 days; not combined with `period`). Every period has a same-length previous period right before it (`summary.created` and `summary.resolved` return `current` and `previous`). `tz` is an IANA name (default UTC, unknown names are rejected); day boundaries and volume buckets follow it.
- **Sections:** `summary`, `volume` (zero-filled; daily up to 31 days, otherwise 7-day buckets counted from the period start), `recent_tickets`, `waiting`, `activity` (ticket events only, source `ticket`; never message text or customer emails). `include=a,b` returns a subset. `recent_limit` (5), `waiting_limit` (5), `activity_limit` (10), each 1 to 50. Unknown query parameters are rejected with 400.
- **Access:** permission code `dashboard.view` for owner and member; non-members and removed members get 404. Access is checked on every call, before the cache.
- **Performance:** cached 30 seconds in Redis per workspace and normalised query (the cache key uses the resolved dates, time zone, sections and limits, not the raw query string); a fixed number of queries (about 10, none per row) whatever the data size; throttle scope `dashboard`, 30 per minute per user. `meta.cached` tells whether the response came from the cache.
- **Not included (deferred with the AI phase):** most-used articles and AI usage metrics. Audit-log rows are not mixed into `activity`.

### Feature 8: Context search and LLM settings (`ai`, `common/llm`, `common/search`, `knowledge`, `tickets`), built 2026-10-22

Endpoints: `POST /api/workspaces/{id}/knowledge/ask/`, `POST /api/workspaces/{id}/knowledge/context/`, `POST /api/workspaces/{id}/tickets/{ticket_id}/context/`, `GET/PATCH /api/workspaces/{id}/llm/`, `DELETE /api/workspaces/{id}/llm/key/`. Permissions: `knowledge.view`, `tickets.view`, `ai.use`. Rules, limits and the reasons for them: DECISION.md, entry of 2026-10-22; request flow: FLOW.md, section 13. Extended 2026-10-23 (RAG over uploaded documents): search is hybrid (words plus pgvector embeddings) over chunks of published articles and READY uploads; uploads are read by pdfplumber and python-docx on the default Celery queue, chunked by heading with page numbers, embedded with `gemini-embedding-001` (768 dims) on the Resolve AI key; results carry `source` {type, id, title, page}. Rules, limits and the reasons: DECISION.md, entry of 2026-10-23. Out of scope: multiple languages per workspace, ticket search, an LLM re-ranker, chat follow-ups.

## Deferred (not in v1)

- **AI/RAG phase (rest):** (text extraction, indexing and embeddings for uploads are built, Feature 8) AI assistant conversations beyond single questions, reply drafts, paraphrase, ticket summaries, category/priority suggestions, AI feedback (1 to 5 stars), AI usage logging, AI dashboard metrics, most-used articles.
- Multiple mailboxes per user, SMTP or non-Google mail, per-member permission customization, advanced analytics and SLAs, customer ticket pages or tokens, legacy .doc uploads.

## Open points still to resolve before their feature starts

- Feature 3: whether workspace logo upload is in v1.
- Feature 6: Google Cloud project, Pub/Sub topic and push endpoint, and Gmail OAuth verification for the required scopes (needed before inbound sync can run in production).
- Feature 1: the Google OAuth client must exist (see `docs/GOOGLE_OAUTH_SETUP.md`) before the sign-in flow can be tried end to end. Allauth details marked "verify" (usersessions fields, mounting only the Google URLs via wrapper views) are confirmed against the installed version while building.
