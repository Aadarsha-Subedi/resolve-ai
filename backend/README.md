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
docker compose up --build                       # db, redis, api on http://localhost:8000
docker compose --profile worker up --build      # also start the Celery worker
docker compose exec api python manage.py migrate
docker compose exec api python manage.py test   # with RESOLVE_AI_USE_SQLITE=true, or against the db service
```

The compose file overrides the DB host and Redis URL so the containers reach each other by service name. The Celery worker does not auto-reload; run `docker compose restart celery` after changing tasks. After changing dependencies, rebuild with `--build`.

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
- `knowledge/` feature 4: articles, categories, PDF/TXT uploads and the shared storage quota (same layout)
- `tickets/` feature 5: tickets, messages, history and the public portal (same layout)
- `email_integration/` feature 6: Gmail grant at sign-in, sending replies and confirmations, inbound sync and push, review list (same layout, plus `clients/`)
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

A user can create workspaces (becoming the owner), belong to several, and join through a join link (1 hour by default, 1 day or 7 days) or an invitation to their Google account. The owner removes members, transfers ownership, deletes the workspace (purged after 7 days) and sets the logo. Endpoint list and rules: [Project.MD](Project.MD), Feature 3. Postman folders: `Workspaces`, `Members`, `Join link`, `Invitations`. The logo upload needs the `RESOLVE_AI_R2_*` variables (the browser PUTs to a signed R2 URL, so allow your frontend origin in the bucket's CORS policy with the PUT method).

## Knowledge base (feature 4)

Articles (Markdown, up to 200 KB), categories (five defaults per workspace) and PDF/TXT uploads (up to 10 MB). Everything is stored in the R2 bucket under `workspaces/{id}/knowledge/` and counts toward the 50 MB per-workspace quota (the logo does not). Uploads use a signed URL: request it (`size` in exact bytes), PUT the file with method PUT and the returned Content-Type, then confirm. Filters: title, status, category. Rules and endpoints: [Project.MD](Project.MD), Feature 4. Postman folder: `Knowledge`. Needs the `RESOLVE_AI_R2_*` variables for uploads (articles also need storage: with an empty bucket they use local disk under `media/`).

## Tickets and public portal (feature 5)

Agents (owner and members) create and work tickets under `/api/workspaces/{id}/tickets/`: per-workspace numbers, fixed categories, priorities, five statuses, internal notes and public replies, history, and filters (status, priority, category, dates, search, waiting for reply). Customers use the public portal with no login: `GET /api/portal/{slug}/` and `POST /api/portal/{slug}/tickets/` (per-IP limit, 5 tickets per email per hour, hidden honeypot field `website`). Public replies are stored as `queued`; emailing them and the portal confirmation arrive with feature 6. Rules and endpoints: [Project.MD](Project.MD), Feature 5. Postman folders: `Tickets`, `Portal (public)`.

## Gmail and email (feature 6)

Gmail is connected by the same Google sign-in (no second flow): the login asks for Gmail send and read access, and the refresh token is stored encrypted. Agents' public replies are emailed from their own Gmail; the portal confirmation goes out from the owner's Gmail; customer replies come back through Pub/Sub push or the "Sync latest mails" button (newest 30 messages) and are matched to tickets by email headers. Only mail that belongs to tickets is stored. Rules, endpoints and the privacy model: [Project.MD](Project.MD), Feature 6; Google Cloud setup (scopes, Pub/Sub): [docs/GOOGLE_OAUTH_SETUP.md](docs/GOOGLE_OAUTH_SETUP.md). Postman folder: `Email (Gmail)`. A running Celery worker is needed for sending (`docker compose --profile worker up`).

Celery beat runs `accounts.purge_deleted_accounts`, `workspaces.purge_deleted_workspaces`, `knowledge.release_stale_uploads`, `email_integration.renew_gmail_watches`, `email_integration.purge_old_review_items` and `accounts.clear_expired_sessions` daily (`docker compose --profile worker` starts a worker; run a beat process for the schedule). Later features plug in through `accounts.services.hooks` (`register_ownership_check`, the `account_event` signal).

Docs: `Project.MD` (v1 feature map and build order), `CLAUDE.md` (rules), `DECISION.md` (decision log), `FLOW.md` (code paths).
