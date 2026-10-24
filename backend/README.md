# ResolveAI backend

Django REST API for ResolveAI. See the root README for the project overview and `CLAUDE.md` for conventions.

## Setup

```bash
cp .env.example .env     # every RESOLVE_AI_* variable is required (empty allowed where noted)
docker compose up -d     # Postgres + Redis
uv sync
uv run python manage.py migrate
uv run python manage.py runserver
```

### Everything in Docker (hot reload)

`Dockerfile.dev` builds the dev image; `docker-compose.yml` builds from it and bind-mounts the code into the container, so edits on your machine reload the dev server immediately.

```bash
docker compose up -d --build                   # db, redis, api, Celery worker and beat
docker compose exec api python manage.py migrate
docker compose exec api python manage.py test   # with RESOLVE_AI_USE_SQLITE=true, or against the db service
```

The compose file overrides the DB host and Redis URL so the containers reach each other by service name. The Celery worker does not auto-reload; run `docker compose restart celery celery-beat` after changing tasks. After changing dependencies, rebuild with `--build`.

### Production image

`Dockerfile.prod` is a multi-stage build (runtime dependencies only, non-root user, gunicorn). `docker compose -f docker-compose.prod.yml up --build -d` runs it without a bind mount. Set `RESOLVE_AI_DEBUG=false`, `RESOLVE_AI_ENVIRONMENT=prod`, secure cookies and real hosts in `.env`.

## Tests and lint

```bash
RESOLVE_AI_USE_SQLITE=true uv run python manage.py test
uv run ruff check . && uv run ruff format .
```

## Layout

- `config/` Django project (settings, Celery, root URLs)
- `common/` shared infrastructure (response, exception, pagination, filter, order, cache, logger, validators, models, serializers, throttling, storage, crypto, observability, email helpers)
- `docs/` LLD and `GOOGLE_OAUTH_SETUP.md` (how to create the Google OAuth client); `postman/` Postman collection and environment (updated with every API change)
- `accounts/` feature 1: Google sign-in (django-allauth), `User` model, device sessions, profile, account deletion, Celery tasks (`models/`, `services/`, `serializers/`, `views/`, `constants/`, `adapters.py`, `tasks.py`, `tests/`)
- `workspaces/` feature 3: workspaces, membership, join links, invitations, ownership transfer, logo (same layout as `accounts/`)
- `knowledge/` feature 4: articles, categories, uploads (PDF, DOCX, Markdown, text) read in the background into searchable passages with embeddings, and the shared storage quota (same layout)
- `tickets/` feature 5: tickets, messages, history and the public portal (same layout)
- `email_integration/` feature 6: Gmail grant at sign-in, sending replies and confirmations, inbound sync and push, review list (same layout, plus `clients/`)
- `ai/` per-user, per-workspace LLM settings, encrypted keys and the daily Resolve AI allowance (same layout); the provider code is in `common/llm/`, the search helpers in `common/search/`
- `audit/` feature 2: append-only audit log fed by every feature's hook signals, owner-only read endpoint
- Feature apps are added one at a time (see the root README)

## Accounts (feature 1)

Set `RESOLVE_AI_GOOGLE_CLIENT_ID`, `RESOLVE_AI_GOOGLE_CLIENT_SECRET`, `RESOLVE_AI_PUBLIC_API_URL` and `RESOLVE_AI_FRONTEND_URL` in `.env`, and register `<origin>/api/auth/google/login/callback/` as a redirect URI in Google Cloud ([docs/GOOGLE_OAUTH_SETUP.md](docs/GOOGLE_OAUTH_SETUP.md)). Whatever proxy sits in front of the API must keep the `Host` header and send `X-Forwarded-Proto`, because the redirect URI is built from the incoming request.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/csrf/` | set the CSRF cookie |
| GET | `/api/auth/google/start/?remember=0\|1&next=/path` | begin sign-in (redirect) |
| GET | `/api/auth/google/login/callback/` | Google's redirect target |
| POST | `/api/auth/logout/`, `/api/auth/logout-all/` | end this session / every session |
| GET | `/api/auth/sessions/` | own device sessions |
| DELETE | `/api/auth/sessions/{id}/` | revoke one device |
| GET, PATCH, DELETE | `/api/me/` | profile, rename, request deletion (7-day grace; signing in again cancels it) |

Postman: Google sign-in cannot finish inside Postman. Sign in with a browser, copy the `sessionid` cookie (DevTools, Application, Cookies) into the `sessionCookie` environment variable; the collection sends it on every request. Run `Auth / CSRF cookie` first for POST, PATCH and DELETE. `sessionId` is a different variable: the numeric device id used by `Revoke session`.

## Workspaces (feature 3)

A user can create workspaces (becoming the owner), belong to several, and join through a join link (1 hour by default, 1 day or 7 days) or an invitation to their Google account. The owner removes members, transfers ownership, deletes the workspace (purged after 7 days) and sets the logo. Endpoint list and rules: [Project.MD](Project.MD), Feature 3. New invitations are also emailed to the invitee from the owner's Gmail (needs the Celery worker). Postman folders: `Workspaces`, `Members`, `Join link`, `Invitations`. The logo upload needs the `RESOLVE_AI_R2_*` variables (the browser PUTs to a signed R2 URL, so allow your frontend origin in the bucket's CORS policy with the PUT method).

## Context search (AI)

`POST /api/workspaces/{id}/knowledge/context/` (`{"query": "..."}`) and `POST /api/workspaces/{id}/tickets/{ticket_id}/context/` (optional `{"message_id"}`) return the best passages from published articles and uploaded files (words and meaning, merged) with citations. `POST /api/workspaces/{id}/knowledge/ask/` also returns an answer paraphrased from those passages with `[n]` citations (the frontend's Ask page) and keeps each user's chats per workspace (`GET/DELETE .../knowledge/ask/conversations/`; run `migrate` after pulling). Users choose Resolve AI or their own Gemini/OpenAI key at `GET/PATCH /api/workspaces/{id}/llm/`. Environment: `RESOLVE_AI_GEMINI_API_KEY` (the Resolve AI key; leave empty to disable it, search still works without query rewriting) and `RESOLVE_AI_LLM_CALL_LIMIT` (calls per user per workspace per day, default 100). The Gemini and OpenAI SDKs are new dependencies: after pulling, run `docker compose build api celery celery-beat` and `docker compose up -d`. Articles that existed before chunking need `docker compose exec api python manage.py reindex_knowledge` once (`--uploads` re-reads every file, `--embeddings` recomputes every embedding). Rules: [DECISION.md](DECISION.md) (2026-10-22) and [FLOW.md](FLOW.md), section 13. Postman requests: `Knowledge` and `Tickets` folders.

## Knowledge base (feature 4)

Articles (Markdown, up to 200 KB), categories (five defaults per workspace) and uploads of PDF, DOCX, Markdown or text files (up to 10 MB each; no legacy .doc). Article text is stored in the database (up to 100 KB each, 100 articles per workspace); uploaded files are stored in the R2 bucket under `workspaces/{id}/knowledge/`. Both count toward the 50 MB per-workspace quota (the logo does not). Uploads use a signed URL: request it (`size` in exact bytes), PUT the file with method PUT and the returned Content-Type, then confirm. Uploaded files are read in the background (on the default Celery worker, pdfplumber and python-docx inside the image, no extra service): `index_status` goes pending, indexing, indexed or failed, and only indexed files are searched. Embeddings use the same `RESOLVE_AI_GEMINI_API_KEY` (model `gemini-embedding-001`, 768 dimensions); without it search uses words only. After pulling: `docker compose build`, `docker compose up -d`, `uv lock` if you changed dependencies, `migrate`. The database image is `pgvector/pgvector:pg17`. Filters: title, status, category. Rules and endpoints: [Project.MD](Project.MD), Feature 4. Postman folder: `Knowledge`. Needs the `RESOLVE_AI_R2_*` variables for uploads (articles also need storage: with an empty bucket they use local disk under `media/`).

## Tickets and public portal (feature 5)

Agents (owner and members) create and work tickets under `/api/workspaces/{id}/tickets/`: per-workspace numbers, fixed categories, priorities, five statuses, internal notes and public replies, an optional assignee (an active member; unassigned automatically when they leave), history, and filters (status, priority, category, dates, search, waiting for reply, assignee). Customers use the public portal with no login: `GET /api/portal/{slug}/` and `POST /api/portal/{slug}/tickets/` (per-IP limit, 5 tickets per email per hour, hidden honeypot field `website`). `GET .../tickets/{id}/overview/` returns the whole ticket page in one request (ticket, conversation, history, your role and permissions, your Gmail status). Public replies are stored as `queued`; emailing them and the portal confirmation arrive with feature 6. Rules and endpoints: [Project.MD](Project.MD), Feature 5. Postman folders: `Tickets`, `Portal (public)`.

## Gmail and email (feature 6)

Gmail is connected by the same Google sign-in (no second flow): the login asks for Gmail send and read access, and the refresh token is stored encrypted. Agents' public replies are emailed from their own Gmail; the portal confirmation goes out from the owner's Gmail; customer replies come back through Pub/Sub push or the "Sync latest mails" button (newest 30 messages) and are matched to tickets by email headers. Only mail that belongs to tickets is stored. Rules, endpoints and the privacy model: [Project.MD](Project.MD), Feature 6; Google Cloud setup (scopes, Pub/Sub): [docs/GOOGLE_OAUTH_SETUP.md](docs/GOOGLE_OAUTH_SETUP.md). Postman folder: `Email (Gmail)`. A running Celery worker is needed for sending (`docker compose up -d --build` starts it).

## Dashboard (feature 7)

Served by the `audit` app (no separate app). `GET /api/workspaces/{id}/dashboard/` returns the whole dashboard screen in one call: ticket counts (active, urgent, high, waiting for reply), tickets created and resolved against the previous period, volume over time, recently updated tickets, tickets waiting for a reply and recent ticket activity. Query: `period` (7d, 30d, 90d) or `from`/`to` (max 366 days), `tz`, `include`, `recent_limit`, `waiting_limit`, `activity_limit`. Owner and members (`dashboard.view`); cached 30 seconds; 30 requests a minute per user. Response shape: [docs/DASHBOARD_API.md](docs/DASHBOARD_API.md); rules: [Project.MD](Project.MD), Feature 7. Postman folder: `Dashboard`.

## Audit log (feature 2)

Sensitive actions (membership and ownership changes, join links, invitations, knowledge-base changes, ticket creation/edits/status changes, account and Gmail connection changes) are recorded automatically from the hook signals each feature emits. The workspace owner reads them at `GET /api/workspaces/{id}/audit/` (filters: action, action_prefix, actor, target, dates). The log is append-only, has no export, and never stores tokens, message text or email addresses. To audit a new action, add it to `audit/constants/actions.py` and emit it from the feature's `hooks.py`. Details: [Project.MD](Project.MD), Feature 2. Postman folder: `Audit`.

Celery beat runs `accounts.purge_deleted_accounts`, `workspaces.purge_deleted_workspaces`, `knowledge.release_stale_uploads`, `knowledge.requeue_unindexed_uploads`, `knowledge.embed_pending_chunks`, `email_integration.renew_gmail_watches`, `email_integration.purge_old_review_items` and `accounts.clear_expired_sessions` daily (`docker compose up -d --build` starts the worker and the `celery-beat` service). Later features plug in through `accounts.services.hooks` (`register_ownership_check`, the `account_event` signal).

Docs: `Project.MD` (v1 feature map and build order), `CLAUDE.md` (rules), `DECISION.md` (decision log), `FLOW.md` (code paths).
