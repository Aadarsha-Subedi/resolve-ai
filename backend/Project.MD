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
- Knowledge base: in-app articles plus PDF/TXT uploads (stored only, no text extraction in v1); 50 MB per workspace; simple filter by title, status, category (no full-text search in v1). Default categories: General, Getting started, Billing, Troubleshooting, FAQ; users can add, rename, delete.
- Gmail: one connection per user; agents send from their own mailbox (no connection, no send); portal confirmation is sent from the owner's mailbox (skipped if none). Inbound via Pub/Sub push plus a "Sync latest mails" button, no polling; matched by headers; unmatched mail goes to a review list.
- Dashboard: open and urgent counts, volume over time, recently updated, waiting for reply (last public message is from the customer), recent activity. No AI metrics.
- Account deletion blocked while owning a workspace; 7-day grace. Workspace deletion by owner, purged after 7 days. Audit log: owner-only list, no export.
- No ticket assignment in v1.

## Feature map and build order

| # | Feature | Depends on | Status |
| --- | --- | --- | --- |
| 0 | Foundation: `common` app, config, Docker, Postman, docs | none | Done |
| 1 | Accounts and sessions (`accounts`) | 0 | Done, breakdown below |
| 2 | Audit log (`audit`) | all other features | Deferred: built last, after every other v1 feature |
| 3 | Workspaces and membership (`workspaces`) | 1 | Done, details below |
| 4 | Knowledge base (`knowledge`) | 3 | Done, details below |
| 5 | Tickets and public portal (`tickets`) | 3 | Done, details below |
| 6 | Gmail connection and email (`email_integration`) | 1, 3, 5 | Planned |
| 7 | Dashboard (`dashboard`) | 3, 5 | Planned |

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

### Feature 2: Audit log (`audit`)

`AuditEvent` model and a `record(actor, workspace, action, target, metadata)` service (never raises, no secrets or message bodies). Owner-only list endpoint with filters (action, actor, date range); no export. Actions are registered as constants as features land.

### Feature 3: Workspaces and membership (`workspaces`), built

Models: `Workspace` (UUIDv7, name, immutable unique slug, `logo_key`, `portal_enabled`, soft delete), `WorkspaceMembership` (OWNER/MEMBER, ACTIVE/REMOVED; database constraints allow one membership per user and one active owner per workspace), `WorkspaceJoinLink` (SHA-256 token hash, `expires_at`, `revoked_at`; one unrevoked link per workspace), `WorkspaceInvitation` (address as typed plus a canonical mailbox key, `expires_at`, `accepted_at`, `closed_at`).

Rules (owner answers of 2026-10-20):
- **Join link:** direct membership, expires after **1 hour** by default; the owner may choose 1 hour, 1 day or 7 days. Creating a link rotates (revokes) the previous one. The raw token and URL (`FRONTEND_URL/join/<token>`) are shown once; status calls return metadata only. Redemption is limited per IP (`join_link` scope); unknown, expired, revoked and deleted-workspace links return the same 404.
- **Invitations:** the owner invites one or several Google accounts (max 20 per request, 7-day expiry, single use). A person sees and accepts invitations for the mailbox they signed in with; acceptance is an explicit step. Gmail addresses are compared by mailbox (`common.email.utils.canonical_email_key`: dots and `+tags` ignored, `googlemail.com` = `gmail.com`), other domains only lower-cased. `x.y@gmail.com` is mailbox `xy`, while `x+y@gmail.com` is mailbox `x`. No invitation email is sent in this feature (Gmail sending is feature 6); the owner tells the person.
- **Roles:** fixed presets in `workspaces/constants/permissions.py` (`OWNER` has every code, `MEMBER` can view the workspace and the member list). Non-members and removed members get 404; members lacking a permission get 403. `WorkspaceAccessPolicy` answers the boolean questions.
- **Ownership transfer** is one transaction (old owner demoted first, then the target promoted). The owner cannot leave or be removed. Removal keeps the membership row (history) and revokes access; a removed person can come back through a link or an invitation as a MEMBER.
- **Deletion:** the owner soft-deletes a workspace; it vanishes for everyone at once and a daily task (`workspaces.purge_deleted_workspaces`) hard-deletes it, and its logo object, after 7 days. `account_ownership_blocker` is registered with the account-deletion check, so an owner must transfer or delete first.
- **Logo:** direct-to-R2 upload with a signed PUT (`logo/upload-url/`, then `PUT logo/` to confirm; the server verifies the object, type and size, 2 MB, PNG/JPEG/WebP). Needs R2 configured.
- Audit: every action calls `workspaces.services.hooks.emit`, a signal the audit app subscribes to later.

Endpoints (under `/api/`): `workspaces/` (GET list, POST create), `workspaces/{id}/` (GET, PATCH name and portal_enabled, DELETE), `workspaces/{id}/transfer-ownership/`, `workspaces/{id}/members/`, `workspaces/{id}/members/{user_id}/` (DELETE), `workspaces/{id}/leave/`, `workspaces/{id}/join-link/` (GET, POST, DELETE), `join-links/redeem/`, `workspaces/{id}/invitations/` (GET, POST), `workspaces/{id}/invitations/{id}/` (DELETE), `invitations/` (mine), `invitations/{id}/accept/`, `invitations/{id}/decline/`, `workspaces/{id}/logo/upload-url/`, `workspaces/{id}/logo/` (PUT, DELETE).

### Feature 4: Knowledge base (`knowledge`), built

Models: `KnowledgeArticle` (draft/published/archived; metadata in the database, the Markdown body is an object in R2), `KnowledgeCategory` (per workspace, unique slug), `KnowledgeArticleCategory` (many-to-many), `KnowledgeUpload` (PDF/TXT metadata; PENDING until the browser upload is confirmed, then READY). `Workspace.storage_used_bytes` holds the quota counter.

Rules (owner answers D5, D6 and the defaults of 2026-10-20):
- **Storage:** the same R2 bucket as the logo, one prefix per workspace: `workspaces/{id}/knowledge/articles/{article_id}.md` and `.../uploads/{upload_id}.pdf|txt`. Keys never contain user-supplied names; the display filename is kept in the database. Articles and uploads (not the logo) all count toward the 50 MB per-workspace quota.
- **Quota:** one conditional `UPDATE` reserves space (articles on save, uploads when the upload URL is issued) so concurrent writers cannot overshoot; it answers 413 `storage_quota_exceeded` when full. Deleting or shrinking frees space. Uploads never confirmed within 1 hour are removed by the hourly task `knowledge.release_stale_uploads`.
- **Articles:** title up to 200 characters, body up to 200 KB (UTF-8 bytes), up to 10 categories. Status changes go through `publish`, `unpublish` (back to draft) and `archive`; PATCH cannot change status. ABAC rule: archived articles are read-only until moved back to draft. Delete is permanent and removes the stored object. A storage failure rolls the row and the quota change back.
- **Uploads:** PDF or TXT, 1 byte to 10 MB, signed direct upload then confirm. Confirm checks exact size and content type (PDFs must start with `%PDF-`) and discards anything else. Downloads are signed URLs that force a download, valid 5 minutes. No text extraction.
- **Filters:** `?title=` (contains), `?status=`, `?category=<id>`, `?ordering=` (title, created_at, updated_at, published_at), plus limit/offset. No full-text search in v1.
- **Categories:** defaults General, Getting started, Billing, Troubleshooting, FAQ are created with each workspace (and by a data migration for existing ones). Owner and members may add, rename and delete them; names are unique per workspace (case-insensitive through the slug); deleting a category only unlinks it.
- **Access:** both roles may view and manage the knowledge base (`knowledge.view`, `knowledge.manage`); non-members get 404.
- When a workspace is purged, its stored article and upload objects are deleted. Audit hook: `knowledge.services.hooks.knowledge_event`.
- Known limit: no versioning. An article save overwrites the stored object, so a crash between the database commit and the storage write is the only way the two can disagree (the write happens last inside the transaction so a failure undoes the rows).

Endpoints (under `/api/workspaces/{workspace_id}/knowledge/`): `articles/` (GET, POST), `articles/{id}/` (GET, PATCH, DELETE), `articles/{id}/publish|unpublish|archive/` (POST), `categories/` (GET, POST), `categories/{id}/` (PATCH, DELETE), `uploads/` (GET), `uploads/upload-url/` (POST), `uploads/{id}/confirm/` (POST), `uploads/{id}/download/` (GET), `uploads/{id}/` (DELETE), `storage/` (GET).

### Feature 5: Tickets and public portal (`tickets`), built

Models: `Ticket` (per-workspace number, subject, description, customer name/email, status, priority, fixed category, `created_via` PORTAL/AGENT/EMAIL, resolved/closed/last-activity timestamps, `last_customer_message_at` and `last_agent_reply_at`, `confirmation_pending`), `TicketMessage` (public or internal, author type, direction, delivery status, and email correlation fields that feature 6 fills), `TicketEvent` (history without message text). `Workspace.last_ticket_number` is the counter behind the numbers.

Rules (owner approved the proposed defaults, 2026-10-20):
- **Numbers:** per workspace from 1 (`#1`), allocated with an `UPDATE ... SET n = n + 1` on the workspace row inside the creating transaction, so concurrent creators queue, there are no duplicates, and a rollback gives the number back.
- **Categories (fixed):** billing, technical, account, feature_request, general (default), other. **Priority:** low, medium (default), high, urgent; customers cannot set it. **Statuses:** open, in_progress, pending, resolved, closed. No assignment, no ticket deletion.
- **ABAC (`tickets/policies.py`):** any member changes status freely, but only the owner moves a ticket out of CLOSED (403 `owner_only_reopen`). On a CLOSED ticket members cannot edit subject, description, customer fields, category or priority (403 `ticket_closed`); the owner can. Nobody can add a public reply to a CLOSED ticket (reopen first); internal notes are still allowed.
- **Messages:** an internal note (never customer-visible) or a public reply, up to 20,000 plain-text characters. A public reply is stored first with delivery status QUEUED; feature 6 sends it from the agent's own Gmail. Messages cannot be edited or deleted. Replies do not change status; "waiting for reply" is computed (last customer message newer than the last agent reply, and the `waiting_for_reply` list filter). The customer's description is stored as the first public message.
- **History:** `TicketEvent` rows for created, status/priority/category/details changed, public reply added, internal note added (message ids, not bodies).
- **Portal (no login, no CSRF):** `GET /api/portal/{slug}/` (name, slug, logo only) and `POST /api/portal/{slug}/tickets/` (email required; name, subject, description, optional category). Unknown slug, deleted workspace and disabled portal all answer the same 404. Protection: per-IP limit (`portal_ticket` scope), at most 5 tickets per customer email per workspace per hour (429 `portal_email_rate_limited`), and a hidden `website` field that, when filled, returns a normal-looking success without creating anything. The response carries only the ticket number. No customer token or ticket page; follow-up is by email (feature 6). Portal tickets are flagged `confirmation_pending` until feature 6 sends the confirmation from the owner's mailbox.
- **Access:** owner and members see every ticket of the workspace; non-members get 404. Audit hook: `tickets.services.hooks.ticket_signal`.

Endpoints: `/api/workspaces/{workspace_id}/tickets/` (GET list with filters `status`, `priority`, `category`, `created_from`, `created_to`, `q`, `waiting_for_reply`, `ordering`; POST create), `tickets/{id}/` (GET, PATCH), `tickets/{id}/status/` (POST), `tickets/{id}/messages/` (GET, POST), `tickets/{id}/events/` (GET), and the public `/api/portal/{slug}/` and `/api/portal/{slug}/tickets/`.

### Feature 6: Gmail connection and email (`email_integration`)

- 6a: `GmailConnection` (one per user, `sub` must equal login `sub`, encrypted refresh token via `common.crypto`, status), connect/disconnect/status endpoints.
- 6b: `EmailDeliveryAttempt`, outbound reply and portal confirmation through Celery, retries with idempotency, delivery status on messages.
- 6c: Pub/Sub push endpoint (verified), `EmailSyncCheckpoint`, "Sync latest mails" endpoint, header-based matching and dedupe, review list for unmatched or ambiguous mail (attach to ticket or dismiss), Gmail watch renewal task.

### Feature 7: Dashboard (`dashboard`)

Read-only, workspace-scoped endpoints: ticket counts (open, urgent), resolved over a period, volume over time, recently updated, waiting for reply, recent activity (from `TicketEvent` and audit). No SLA or response-time claims.

## Deferred (not in v1)

- **AI/RAG phase (after the backend and frontend exist):** PostgreSQL full-text search, text extraction and indexing for uploads, Gemini client, retrieval and citations, AI assistant Q&A and conversations, reply drafts, paraphrase, ticket summaries, category/priority suggestions, AI feedback (1 to 5 stars), AI usage logging, AI dashboard metrics, most-used articles.
- Ticket assignment, multiple mailboxes per user, SMTP or non-Google mail, per-member permission customization, advanced analytics and SLAs, customer ticket pages or tokens, DOCX uploads.

## Open points still to resolve before their feature starts

- Feature 3: whether workspace logo upload is in v1.
- Feature 6: Google Cloud project, Pub/Sub topic and push endpoint, and Gmail OAuth verification for the required scopes (needed before inbound sync can run in production).
- Feature 1: the Google OAuth client must exist (see `docs/GOOGLE_OAUTH_SETUP.md`) before the sign-in flow can be tried end to end. Allauth details marked "verify" (usersessions fields, mounting only the Google URLs via wrapper views) are confirmed against the installed version while building.
