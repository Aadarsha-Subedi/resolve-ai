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
