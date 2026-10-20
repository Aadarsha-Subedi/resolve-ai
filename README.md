# ResolveAI

A capstone project that uses AI to resolve customer queries: a multi-tenant support desk where customers submit tickets through a public workspace portal, and agents answer them with Gmail-based email and AI help grounded in the workspace's knowledge base. AI drafts replies; a human always reviews and sends.

## Status

| Area | State |
| --- | --- |
| Design (LLD) | Draft, owner decisions applied: [backend/docs/ResolveAI_LLD.md](backend/docs/ResolveAI_LLD.md) |
| Backend | In progress. `common` app and config done; features 1 (accounts and sessions), 3 (workspaces and membership) and 4 (knowledge base) and 5 (tickets and portal) built; Gmail and email next; audit log built last |
| Frontend | Not started |
| LLM layer (full-text search, Gemini) | After frontend and backend scaffolding |

## Repository layout

```
resolve-ai/
  README.md      this file (kept current as the project evolves)
  backend/       Django REST API: code, docs/ (LLD), postman/, CLAUDE.md, DECISION.md, FLOW.md
  frontend/      React + TypeScript app (not started)
```

## Stack

- **Backend:** Django 6.1 + Django REST Framework, PostgreSQL, Redis, Celery, managed with `uv` (Python 3.14)
- **Frontend:** React + TypeScript
- **Auth:** Google OAuth with server-side Django sessions
- **Email:** Gmail API (OAuth); inbound mail via Pub/Sub push plus a manual sync button
- **AI:** Gemini API, with PostgreSQL full-text search over published knowledge-base content

## Backend

Built so far (`backend/common/`): response envelope, exception handling with stable error codes, pagination/filter/order helpers, strict serializers, model mixins (timestamps, soft delete, cache), request-id logging, Sentry hook, throttling (including per-workspace), file storage (R2/local/in-memory), Fernet encryption helper, `/api/health/`.

Feature 1, `backend/accounts/`: Google-only sign-in through django-allauth (redirect flow with PKCE), custom UUIDv7 `User` without a password, 14-day sessions (30 days with remember me), device session list with revoke-one and log-out-everywhere, `/api/me/` profile, and account deletion with a 7-day grace period. Needs `RESOLVE_AI_GOOGLE_CLIENT_ID` and `RESOLVE_AI_GOOGLE_CLIENT_SECRET` in `backend/.env` (see `backend/docs/GOOGLE_OAUTH_SETUP.md`).

Feature 3, `backend/workspaces/`: workspaces with an owner and members, join links (1 hour by default) and invitations to Google accounts, ownership transfer, deletion with a 7-day grace period, and a logo stored in R2.

Feature 4, `backend/knowledge/`: knowledge-base articles with categories and PDF/TXT uploads, all stored in R2 under the workspace and counted in a 50 MB per-workspace quota; filters by title, status and category.

Feature 5, `backend/tickets/`: tickets with notes, replies and history for the team, and a public portal where customers submit tickets without logging in (rate limited, honeypot).

v1 (backend only, no AI/RAG) is mapped in [backend/Project.MD](backend/Project.MD). Build order: accounts and sessions, workspaces, knowledge base, tickets and portal, Gmail and email, dashboard, then the audit log last. The `ai` app (full-text search, Gemini) comes after.

Quick start:

```bash
cd backend
cp .env.example .env        # fill in the values
docker compose up -d        # Postgres + Redis (or `docker compose up --build` for the API too, with hot reload)
uv sync
uv run python manage.py migrate
uv run python manage.py runserver
uv run python manage.py test
```

Backend conventions, guardrails and confirmed product decisions are in `backend/CLAUDE.md`. Every meaningful change is logged in `backend/DECISION.md`; code paths are traced in `backend/FLOW.md`.

API requests are kept in `backend/postman/` (collection and environment), updated with every API change.

## Frontend

Not started. It will be added in `frontend/` after the backend foundation is in place.

## Key product decisions

- Google-only sign-in; OWNER and MEMBER roles; RBAC permissions plus fixed ABAC rules.
- RESOLVED and CLOSED are separate ticket states; only the owner reopens CLOSED.
- Customers follow tickets by email only; internal notes never reach customers.
- Knowledge base: in-app articles plus PDF/TXT uploads, 50 MB per workspace.
- AI never sends or changes anything on its own; answers cite real retrieved articles.

Open points are tracked in section 14 of the LLD.
