# DECISION.md

Log of meaningful decisions that change the codebase. Append only; supersede with a new entry instead of editing old ones.

Format: **Date, title** / Decision / Reason / Alternatives / Files.

---

## 2026-10-16, Build the `common` app before any feature
- **Decision:** port the reusable infrastructure from the owner's project-management backend into `common/` first, then build features on it.
- **Reason:** the owner asked for shared patterns (response envelope, exceptions, pagination, storage, logging, throttling) to exist before ResolveAI features so every module is consistent.
- **Alternatives:** write each app's own helpers (rejected: duplication and drift).
- **Files:** `common/**`, `config/**`.

## 2026-10-16, Pieces left out of the port
- **Decision:** dropped the password, disposable-email and tag validators, the OpenAPI envelope schema, Slack/integrations, allauth, and the project-membership code.
- **Reason:** ResolveAI is Google-only (no passwords), has no tags, and those pieces belong to other features. OpenAPI can be added later when endpoints exist.
- **Files:** `common/validators/`, `config/settings.py`.

## 2026-10-16, `ProjectThrottle` renamed `WorkspaceThrottle`
- **Decision:** the per-tenant throttle keys on a `workspace_id` URL kwarg with scope `workspace`.
- **Reason:** the tenant in ResolveAI is the workspace.
- **Files:** `common/throttling/scoped.py`, `config/settings.py`.

## 2026-10-16, `common/crypto.py` added
- **Decision:** a Fernet `MultiFernet` helper (`encrypt`, `decrypt`, `rotate`) reading `ENCRYPTION_KEYS`.
- **Reason:** Gmail refresh tokens must be encrypted at rest with key rotation (LLD 3.6). Adapted from the reference `integrations/crypto.py`, without the integrations dependency.
- **Files:** `common/crypto.py`, `config/settings.py`, `common/tests/test_common.py`.

## 2026-10-16, Settings and env naming
- **Decision:** env vars use the `RESOLVE_AI_` prefix and are all required (empty allowed where noted); Postgres + Redis via docker-compose; SQLite escape hatch for tests; cached_db sessions with a sliding 14-day (30-day remember-me) lifetime.
- **Reason:** mirrors the proven reference config; remember-me and session management are v1 per the owner.
- **Files:** `config/settings.py`, `.env.example`, `docker-compose.yml`.

## 2026-10-16, Product decisions recorded in the LLD
- RESOLVED and CLOSED stay separate; only the owner reopens CLOSED.
- Workspace slug is immutable.
- Customer follow-up is email only; no per-ticket customer access token (the `CustomerTicketAccessToken` model is removed from v1).
- Knowledge base accepts in-app articles plus PDF/TXT uploads; per-workspace upload limit 50 MB; ingestion is built after the frontend/backend scaffolding, together with FTS and Gemini.
- AI conversations are private per user per workspace.
- Ticket categories are a fixed list; knowledge categories ship with defaults and are user-editable. (Assumed from the owner's wording; confirm.)
- Inbound Gmail uses Pub/Sub push plus a manual "sync latest mails" button; no polling.
- AI feedback is a 1 to 5 star rating with an optional description, scoped to the user; replaces article-level `ArticleFeedback`.
- ABAC rules are fixed in code and not configurable; RBAC permission codes extend with ABAC state conditions.
- "Waiting for reply" means the last public message was sent by the customer, so the ticket awaits an agent. (The owner wrote "sent by the user"; this reading is assumed. Confirm.)
- Remember-me, per-device session list, revoke-one-device and log-out-everywhere are in v1.
- **Reason:** owner answers of 2026-10-16.
- **Files:** `docs/ResolveAI_LLD.md`, `CLAUDE.md`.

## 2026-10-16, Monorepo root and Postman files
- **Decision:** the repo root contains only `frontend/`, `backend/` and `README.md`; the LLD lives in `backend/docs/`. `backend/postman/` holds `resolveai.postman_collection.json` and `resolveai.postman_environment.json`, updated with every API change (rule added to CLAUDE.md).
- **Reason:** owner's instruction; keeps the root clean and API examples always current.
- **Files:** `README.md`, `backend/CLAUDE.md`, `backend/postman/*`, `backend/docs/ResolveAI_LLD.md`.

## 2026-10-20, Dockerfiles for dev and prod; compose builds from them
- **Decision:** added `Dockerfile.dev` (dev dependencies, Django `runserver`) and `Dockerfile.prod` (multi-stage, no dev dependencies, non-root user, gunicorn) plus `.dockerignore`. `docker-compose.yml` now builds the `api` (and optional `celery`, profile `worker`) service from `Dockerfile.dev` and bind-mounts `.:/app` for hot reload. `docker-compose.prod.yml` builds from `Dockerfile.prod` with no bind mount.
- **Reason:** owner asked for Dockerfiles with compose referencing them, and hot reloading in development. The virtualenv is installed at `/opt/venv` so the bind mount over `/app` does not hide it. Compose overrides `RESOLVE_AI_DB_HOST`, `RESOLVE_AI_DB_PORT` and `RESOLVE_AI_REDIS_URL` so containers reach `db` and `redis` by service name while `.env` keeps host values for non-Docker runs.
- **Alternatives:** one multi-stage Dockerfile with dev/prod targets (rejected: the owner asked for separate dev and prod files, as in the reference project).
- **Not done:** `collectstatic`/static serving is not configured (no `STATIC_ROOT` yet), and the Celery worker has no auto-reload.
- **Files:** `backend/Dockerfile.dev`, `backend/Dockerfile.prod`, `backend/.dockerignore`, `backend/docker-compose.yml`, `backend/docker-compose.prod.yml`, `backend/README.md`, `backend/CLAUDE.md`, `README.md`.

## 2026-10-20, v1 scope: backend only, no AI/RAG; feature map in Project.MD
- **Decision:** v1 contains accounts and sessions, audit log, workspaces, knowledge base, tickets and portal, Gmail connection and email, and dashboard, built in that order. All AI/RAG work is deferred. Detail in `Project.MD`.
- **Details confirmed by the owner:** KB uploads are stored only (no text extraction) with a 50 MB workspace limit; KB search is a title/status/category filter (no full-text search); ticket categories Billing, Technical, Account, Feature request, General, Other; default KB categories General, Getting started, Billing, Troubleshooting, FAQ; fixed role presets; portal on by default with owner toggle, honeypot + rate limit, no attachments or CAPTCHA; agents send only from their own Gmail, portal confirmation from the owner's Gmail; Pub/Sub + manual sync with a review list for unmatched mail; dashboard without AI metrics; account and workspace deletion with a 7-day grace; owner-only audit list.
- **Reason:** owner wants the backend built first, without the RAG features.
- **Files:** `backend/Project.MD`.

## 2026-10-20, Google sign-in uses the backend-driven authorization code flow (PKCE) with redirects
- **Decision:** feature 1 signs users in with `GET /auth/google/start/` and `GET /auth/google/callback/` (code + PKCE, server-side code exchange, signed `SameSite=Lax` state cookie). No Google JavaScript, iframe, popup or One Tap. This replaces the earlier plan of the frontend sending an ID token to `POST /auth/google/`.
- **Reason:** the previous project's Google button did not work in some browsers; its code ended on a full-page `form_post` redirect to avoid blockers and iframes. That flow still needs a `SameSite=None; Secure` cookie for a cross-site POST, which Safari rejects on `http://localhost`. A GET callback works with a Lax cookie in every browser and needs no third-party cookies. The failure causes are inferred from that code and its comments, not from a bug report.
- **Alternatives:** Google Identity Services button/popup (rejected: the failures above); implicit `form_post` redirect as before (rejected: SameSite=None cookie); frontend-held ID token (rejected: needs the GIS script).
- **Files:** `backend/Project.MD`, `backend/docs/GOOGLE_OAUTH_SETUP.md`, `backend/README.md`.

## 2026-10-20, Feature 1 uses django-allauth (supersedes the hand-written Google flow and the earlier "allauth dropped" entry)
- **Decision:** accounts use `django-allauth[socialaccount]`: Google provider (code flow, PKCE, state, account linking by `sub`) and `allauth.usersessions` (device session list and revoke). We write the `User` model (no password, UUIDv7), a social-account adapter (rules, redirects), our own JSON endpoints in the response envelope for sessions and profile, and account deletion with a 7-day grace. Google `sub` is read from `SocialAccount.uid`, not stored on `User`. Only the Google provider URLs are mounted; allauth's password/signup/HTML pages and headless API are not exposed. The redirect URI becomes `/api/auth/google/login/callback/`.
- **Reason:** the owner asked why allauth was not used. It covers the OAuth flow, sessions list and remember-me with maintained code, so we avoid hand-writing and securing them. The browser-compatibility reasoning is unchanged: allauth's flow is a full-page redirect with a GET callback and a Lax session cookie, with no Google script, iframe or popup.
- **Alternatives:** hand-written flow (earlier plan; rejected as more code to maintain), allauth headless API (rejected: its responses do not use our envelope and it adds surface we do not need).
- **Files:** `backend/Project.MD`, `backend/docs/GOOGLE_OAUTH_SETUP.md`.

## 2026-10-20, Throttling of the Google sign-in endpoints
- **Decision:** allauth 65.20.0 rate-limits only its account views (`ACCOUNT_RATE_LIMITS`); its Google provider and usersessions code have none. Our `start` view and a wrapper around allauth's callback use `common.throttling.scoped` (`AnonThrottle` + `AuthScopedThrottle`, scope `google`, 20/min per IP), and throttled requests redirect to `/login?google_error=rate_limited`. JSON endpoints use the default throttles, with a stricter `account_delete` scope.
- **Reason:** owner asked what rate limiting allauth provides for feature 1; one throttling mechanism for the whole API is easier to configure and test than mixing allauth's limiter in.
- **Files:** `backend/Project.MD`.

## 2026-10-20, Feature 1 built: allauth settings, verified behaviour and deviations
- **Decision:** `accounts` app implemented on django-allauth 65.20.0 (installed with `django-allauth[socialaccount]`). Owner answers: env names use the `RESOLVE_AI_` set, redirects use `RESOLVE_AI_FRONTEND_URL`, sessions last 14 days (30 with remember me), signing in during the grace period cancels deletion, an audit hook exists now, `SessionMeta` only if needed, dependency approved.
- **Verified against allauth 65.20.0 ("verify" items):** `UserSession` has `created_at` and `last_seen_at` but no remember-me flag. The flag is not needed by the API, so `SessionMeta` was **not** added. `UserSession.pk` is an integer, so session ids in the API are integers scoped to the owner (other users get 404). Only the Google callback and a start view are mounted; allauth's own account URLs and `google/login/token/` are not routable. The OAuth redirect URI is built from the request host (`reverse("google_callback")`), so `PUBLIC_API_URL` is only a documented setting; the proxy must preserve `Host` and send `X-Forwarded-Proto`.
- **Deviations from Project.MD:** (1) later logins refresh `avatar_url` only; `display_name` is filled on first login and not overwritten, so a name chosen with `PATCH /me/` survives. (2) `SESSION_SAVE_EVERY_REQUEST = True` so the session lifetime is really sliding as documented. (3) `User` also has `is_staff` (Django admin needs it). (4) The log middleware now redacts cookies, `X-CSRFToken`, `id_token` and the `code`/`state` query values, because the OAuth callback URL carries a single-use code and the session cookie was being logged.
- **Reason:** keep one throttling mechanism and the response envelope; never let an OAuth code, session id or token reach logs or responses.
- **Alternatives:** allauth headless API and its HTML pages (rejected, as before); a `SessionMeta` table (not needed).
- **Files:** `accounts/**`, `config/settings.py`, `config/urls.py`, `common/logger/*`, `pyproject.toml`, `uv.lock`, `postman/*`, `README.md`, `../README.md`, `FLOW.md`, `Project.MD`.

## 2026-10-20, Audit log (feature 2) moves to the end of the v1 build order
- **Decision:** build order is now accounts, workspaces, knowledge base, tickets and portal, Gmail and email, dashboard, then audit. Feature numbers are unchanged so existing references stay valid.
- **Reason:** owner: audit is written once, against the finished product, instead of being updated every time a feature adds actions.
- **Consequences:** workspaces no longer depends on audit; the dashboard's "recent activity" uses `TicketEvent` only until audit exists. Features still emit their own hook or signal for sensitive actions (as `accounts.services.hooks.account_event` already does) so audit can subscribe later without touching feature code.
- **Alternatives:** keep audit second and extend it per feature (rejected by the owner).
- **Files:** `Project.MD`, `CLAUDE.md`, `../README.md`.

## 2026-10-20, Feature 3 built: workspaces, membership, join links, invitations
- **Decision:** `workspaces` app implemented (details in `Project.MD`, Feature 3). Owner answers: the join link expires after 1 hour by default (owner may choose 1 hour, 1 day or 7 days) and the owner can also invite one or several Google accounts; invitations are single-use, expire after 7 days, and are accepted explicitly by the matching signed-in account; Gmail mailboxes are matched with a canonical key (dots, `+tags` ignored, `googlemail.com` = `gmail.com`), other domains only lower-cased.
- **Choices I made (change on request):** one live join link per workspace (creating one revokes the previous); no invitation email until feature 6; the owner can re-invite someone who was removed; a removed person can rejoin through a link or an invitation as a MEMBER; the workspace logo uses a signed direct upload to R2 with a server-side check on confirm (2 MB, PNG/JPEG/WebP) and needs R2 configured; slug is optional on create (derived from the name plus a random suffix) and reserved words are blocked; non-members and removed members get 404, members missing a permission get 403; validation errors can be returned before the 404 for non-members (the 400 does not reveal whether the workspace exists).
- **Reason:** keep invitations tied to the real Google mailbox so Gmail's equivalent spellings cannot create duplicates or let the wrong account in, while keeping the raw join token out of storage and logs.
- **Alternatives:** matching invitations on the exact typed email (rejected: `x.y@gmail.com` and `xy@gmail.com` are the same mailbox); multiple simultaneous join links (not asked for); server-side multipart logo upload (rejected: the shared parsers are JSON-only and R2 signed uploads are already in `common/storage`).
- **Files:** `workspaces/**`, `common/email/utils.py` (`canonical_email_key`), `common/throttling/scoped.py` (`IPScopedThrottle`), `config/settings.py`, `config/urls.py`, `postman/*`, `README.md`, `../README.md`, `FLOW.md`, `Project.MD`, `CLAUDE.md`.

## 2026-10-20, Feature 4 built: knowledge base on R2 with one shared quota
- **Decision:** `knowledge` app implemented (details in `Project.MD`, Feature 4). Owner answers: D5, the knowledge base uses the same bucket as the logo, separated by workspace prefix (`workspaces/{id}/knowledge/...`); D6, articles and documents are all stored in R2 and all count toward the 50 MB workspace quota. All other points followed my proposed defaults, which the owner did not change.
- **Choices I made (change on request):** the article body is a Markdown object in R2 and only metadata is in the database (so filters are plain queries; later full-text search and AI will need an indexed copy of the text); article body limit 200 KB; uploads PDF/TXT up to 10 MB with a signed direct upload plus a confirm step that checks exact size, content type and the `%PDF-` signature; quota is a counter on `Workspace` changed by single conditional UPDATE statements, reserved when the upload URL is issued and released on delete or when an unconfirmed upload goes stale (1 hour, hourly task); the logo is not counted; owner and members both manage articles, uploads and categories; archived articles are read-only (ABAC rule) and PATCH cannot change status; articles are hard-deleted, there is no trash or versioning; category names are unique per workspace through the slug; deleting a category only unlinks it; the object key never contains the user's filename.
- **Reason:** keep one quota and one storage path for everything a workspace stores, with no per-request user-controlled keys and no way for two concurrent uploads to exceed the limit.
- **Alternatives:** article bodies in the database (rejected by D6); a second bucket for the knowledge base (rejected by D5); counting quota only at confirm (rejected: concurrent uploads could overshoot); a content-addressed or versioned article store (not needed in v1).
- **Files:** `knowledge/**`, `workspaces/models/workspace.py` (`storage_used_bytes`), `workspaces/constants/permissions.py`, `config/settings.py`, `config/urls.py`, `postman/*`, `README.md`, `../README.md`, `FLOW.md`, `Project.MD`.

## 2026-10-20, Feature 5 built: tickets, messages, history and the public portal
- **Decision:** `tickets` app implemented (details in `Project.MD`, Feature 5). The owner approved the proposed defaults as written: categories billing, technical, account, feature_request, general (default), other; priorities low/medium/high/urgent (default medium); five statuses; per-workspace ticket numbers from 1; agent-created tickets allowed; internal notes and public replies that cannot be edited or deleted; plain text up to 20,000 characters; no automatic status changes; no assignment, attachments or ticket deletion; the portal with per-IP limit, a 5-per-email-per-hour cap, and a honeypot; no customer token.
- **Choices I made inside those defaults (change on request):** the customer's description is also stored as the first public message of the conversation; a note is still allowed on a CLOSED ticket while public replies are not (not even for the owner until reopened); the owner can edit protected fields of a closed ticket; the honeypot field is named `website` and a filled one returns a random plausible ticket number and creates nothing; the per-email counter lives in the cache (a cache flush resets it); unknown slug, disabled portal and deleted workspace all return the same 404; the portal and customer are not told anything about the workspace beyond name, slug and logo; `TicketEvent` stores message ids, never bodies; email correlation columns exist on `TicketMessage` now (empty until feature 6) with a unique constraint per workspace on a non-empty `email_message_id`; ticket numbers come from `Workspace.last_ticket_number` (an extra workspaces migration).
- **Reason:** gapless, race-free numbers without a sequence per workspace; one place (`create_ticket`) that every channel goes through, so agent, portal and later email tickets behave the same.
- **Alternatives:** a database sequence per workspace (not portable); numbering from `MAX(number)+1` (races); a captcha on the portal (rejected by the owner); automatic PENDING on reply (rejected, agents set status).
- **Files:** `tickets/**`, `workspaces/models/workspace.py` (`last_ticket_number`), `workspaces/constants/permissions.py`, `config/settings.py`, `config/urls.py`, `postman/*`, `README.md`, `../README.md`, `FLOW.md`, `Project.MD`.

## 2026-10-20, Feature 6 built: Gmail through the single sign-in flow
- **Decision:** `email_integration` app implemented (details in `Project.MD`, Feature 6). Owner decisions: one flow only, Gmail scopes (`gmail.send`, `gmail.readonly`, offline access) are requested at Google sign-in and no "Connect Gmail" flow or second callback exists; unrelated mail is never stored; the manual sync reads at most the newest 30 inbox messages; the review list keeps the newest 30 per user for 30 days; unmatched mail is only kept when the sender is a known customer. This supersedes the earlier plan (Project.MD of 2026-10-16) of a separate Gmail OAuth consent.
- **Choices I made (change on request):** declining the Gmail permission still lets the user sign in (status `not_connected`, with a `reconnect_path`); Google sends a refresh token only on first consent, so `?reconnect=1` forces `prompt=consent` (also for signed-in users, which also fixed the signed-in shortcut of `/auth/google/start/` that DRF's anonymous user had disabled); granted scopes are read from Google's `tokeninfo`; the Gmail REST API is called with `requests` instead of adding google-api-python-client; a reply is matched by headers *and* the sender must be the ticket's customer; the portal confirmation is stored as a `system` message so replies to it thread; replies go out from the sending agent's own mailbox with the Gmail thread id of that mailbox; temporary errors retry 3 times; no automatic retry of permanent failures, agents use "resend"; the first push/sync only records the starting history position (no backfill); Pub/Sub pushes must carry a Google-signed JWT for the configured audience and service account; `config/__init__.py` now loads the Celery app so tasks run (eagerly in tests).
- **Reason:** least surprise for users (one consent at sign-in), and the smallest possible copy of someone's mailbox. The ticket's own messages are the history for the later AI phase; Gmail's `threadId` is per mailbox, so it is only used for correlation.
- **Alternatives:** a second Gmail OAuth flow (rejected by the owner); storing tokens in allauth's `SocialToken` (plaintext, rejected); matching by subject (rejected, spoofable); mirroring the inbox (rejected for privacy); polling (rejected earlier).
- **Not done / needs setup:** Google Cloud: enable the Gmail API, add the two scopes under Data Access, add test users (Testing mode refresh tokens expire after 7 days), and for push enable Pub/Sub, create the topic and subscription (push, with authentication). The real Gmail calls have not been run against Google; they are covered with mocked HTTP and a fake client.
- **Files:** `email_integration/**`, `tickets/models/message.py` and `tickets/constants/enums.py` (+ migration), `tickets/services/message_service.py`, `accounts/views/google.py`, `config/settings.py`, `config/__init__.py`, `config/urls.py`, `.env.example`, `postman/*`, `docs/GOOGLE_OAUTH_SETUP.md`, `README.md`, `../README.md`, `FLOW.md`, `Project.MD`.

## 2026-10-20, One read endpoint per screen: ticket overview
- **Decision:** `GET /api/workspaces/{workspace_id}/tickets/{ticket_id}/overview/` returns the ticket (detail), the viewer's role and permission codes, the newest messages and events (`?messages_limit=`, `?events_limit=`, 1-100, default 50, chronological order, totals in `meta`) and an `email` block with the viewer's own Gmail status. The separate ticket, messages and events endpoints stay. A rule was added to `CLAUDE.md`: a screen must not need a fan-out of requests.
- **Reason:** the owner does not want the frontend to fan out five requests to draw the ticket page. The five calls I assumed were ticket, messages, events, workspace/role and Gmail status; the owner confirmed with "make the changes".
- **Choices I made:** the extra blocks come from a registry (`overview_service.register_extra`), so `tickets` does not import `email_integration` (which already depends on `tickets`); only the newest N messages and events are returned, with older ones fetched from the paginated endpoints; the endpoint is read-only; permission codes are returned so the UI can hide actions (the server still enforces everything); the workspace's name and logo are not included (the app already has them from the workspace list; say if the page also needs them).
- **Alternatives:** a generic "batch" endpoint taking a list of requests (rejected: harder to secure and test); GraphQL (not in the stack); `?include=` flags on the detail endpoint (rejected: a dedicated shape is simpler to document and cache).
- **Files:** `tickets/services/overview_service.py`, `tickets/views/ticket.py`, `tickets/serializers/*`, `tickets/urls.py`, `email_integration/apps.py`, `email_integration/services/overview.py`, `postman/*`, `Project.MD`, `FLOW.md`, `README.md`, `CLAUDE.md`.

## 2026-10-20, Audit log built (feature 2, last in the build order)
- **Decision:** `audit` app implemented (details in `Project.MD`, Feature 2). It subscribes to the hook signals every feature already emits, so feature code never calls it. Owner-only read endpoint with filters, no export, no write methods; rows are append-only.
- **Choices I made (change on request):** the list of recorded actions is one table (`audit/constants/actions.py`) and unregistered actions are ignored; replies and notes are not audited (the ticket's history already holds them, and message text must not enter the log); logins, logouts and profile edits are not audited (noise) while log-out-everywhere, session revocation, account deletion steps and Gmail connection changes are, as account-level rows without a workspace that the workspace API never returns; `workspace.purged` is not recorded because the rows go with the workspace (cascade); the actor's display name is copied into the row so the log still reads after the account is deleted; knowledge hooks now carry the target id (`target_id`) and a new `email_integration` hook signal reports Gmail connected/reauthorisation needed/disconnected; metadata is sanitised (secret-like keys dropped, emails masked, nested values dropped, size capped); no retention limit and no IP storage in v1; `audit.view` is held by OWNER only, so after an ownership transfer the previous owner can no longer read the log.
- **Reason:** one place decides what is audited and what is safe to keep, and a failure in auditing can never break the action being audited.
- **Alternatives:** calling `record()` from every service (rejected: edits every feature each time, which is why the audit log was built last); auditing replies and notes (rejected: content); storing IP hashes (not justified yet).
- **Files:** `audit/**`, `knowledge/services/*.py` (target ids), `email_integration/services/hooks.py` and `connection_service.py`, `workspaces/constants/permissions.py`, `config/settings.py`, `config/urls.py`, `postman/*`, `Project.MD`, `FLOW.md`, `README.md`, `../README.md`, `CLAUDE.md`.

## 2026-10-20, Feature 7 built: dashboard (one endpoint)
- **Decision:** a single read endpoint, served by the existing `audit` app (owner decision: no separate `dashboard` app; files `audit/views/dashboard.py`, `audit/services/dashboard_{service,metrics,period}.py`, `audit/serializers/dashboard_{requests,responses}.py`, `audit/constants/dashboard.py`, tests `audit/tests/test_dashboard_*.py`), `GET /api/workspaces/{workspace_id}/dashboard/`, that returns the summary, volume, recent tickets, waiting list and activity in one response (details in `Project.MD`, Feature 7, and the JSON shape in `docs/DASHBOARD_API.md`). The owner confirmed the draft decisions D1 to D12 ("A-F all look good") and asked for the endpoint to be singular.
- **Definitions:** active = open/in_progress/pending; urgent = active + priority urgent, high counted separately; waiting for reply = last customer message later than last agent reply (or no agent reply), active tickets only; resolved is counted by `resolved_at`; period 7d/30d/90d or from/to (max 366 days) with a same-length previous period; `tz` default UTC, invalid rejected; `include=` subset; limits 1 to 50; unknown parameters rejected.
- **Choices I made (change on request):** new permission code `dashboard.view` for owner and member; throttle scope `dashboard` at 30/min per user (plus the per-workspace cap); 30-second cache keyed on workspace + resolved dates + time zone + sections + limits (so `period=7d` and the same dates as `from`/`to` share an entry, and a new day starts a new entry), access checked before the cache; `meta.cached` in the response; weekly buckets are 7 days counted from the period start (not calendar weeks) and are used for periods over 31 days; day-level counts use `TruncDate(tzinfo=...)` and are folded into buckets in Python, so the query count does not depend on the period length; `activity` exposes ticket id, number, subject, event type, actor display name and, only for status/priority/category changes, the old and new enum values; `recent_tickets` and `waiting` omit customer email; the earlier `GET .../tickets/{id}/overview/` is unrelated and unchanged.
- **Bug fixed on the way:** `change_status` overwrote `resolved_at` when the owner reopened a closed ticket straight to resolved; it now keeps the first value (set on first entry to resolved or closed, cleared only on return to an active status). Covered by a test.
- **Schema:** one migration, `tickets/0003_dashboard_indexes`, adding indexes on `(workspace, resolved_at)` and `(workspace, created_at)` for the period counts.
- **Reason:** the screen should not fan out requests (see the 2026-10-20 entry on the ticket overview); one cached, bounded, workspace-scoped read keeps load and access rules in one place.
- **Alternatives:** one endpoint per widget (rejected by the owner); mixing audit rows into activity (rejected: owner-only data and the audit log is a separate feature); calendar-week buckets (rejected: partial first and last weeks are confusing for a custom range); caching per user (rejected: the data is the same for every member).
- **Files:** `audit/**/dashboard*`, `audit/urls.py`, `audit/constants/messages.py`, `tickets/models/ticket.py`, `tickets/migrations/0003_dashboard_indexes.py`, `tickets/services/ticket_service.py`, `workspaces/constants/permissions.py`, `config/settings.py`, `config/urls.py`, `postman/*`, `docs/DASHBOARD_API.md`, `Project.MD`, `FLOW.md`, `README.md`, `../README.md`.
