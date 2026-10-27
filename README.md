# ResolveAI

A capstone project that uses AI to resolve customer queries: a multi-tenant support desk where customers submit tickets through a public workspace portal, and agents answer them with Gmail-based email and AI help grounded in the workspace's knowledge base. AI drafts replies; a human always reviews and sends.

## Status

| Area                                 | State                                                                                                                                                                                                                      |
| ------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Design (LLD)                         | Draft, owner decisions applied: [backend/docs/ResolveAI_LLD.md](backend/docs/ResolveAI_LLD.md)                                                                                                                             |
| Backend                              | Features 1 to 7 built (accounts, workspaces, knowledge, tickets with assignment, Gmail incl. invitation emails, audit, dashboard); `ai` app next. `docker compose up -d --build` in `backend/` starts api, worker and beat |
| Frontend                             | Screens built (not yet run against a live backend); design system awaiting approval: [frontend/README.md](frontend/README.md)                                                                                              |
| LLM layer (full-text search, Gemini) | After frontend and backend scaffolding                                                                                                                                                                                     |

## Repository layout

```
resolve-ai/
  README.md      this file (kept current as the project evolves)
  backend/       Django REST API: code, docs/ (LLD), postman/, CLAUDE.md, DECISION.md, FLOW.md
  frontend/      React + TypeScript app: README.md, PROJECT.md, DECISION.md, FLOW.md
```

## Stack

- **Backend:** Django 6.1 + Django REST Framework, PostgreSQL, Redis, Celery, managed with `uv` (Python 3.14)
- **Frontend:** React 19 + TypeScript, Vite, TanStack (Router, Query, Table), Tailwind v4 + shadcn/ui, pnpm
- **Auth:** Google OAuth with server-side Django sessions
- **Email:** Gmail API (OAuth); inbound mail via Pub/Sub push plus a manual sync button
- **AI:** Gemini API, with PostgreSQL full-text search over published knowledge-base content

## Backend

Built so far (`backend/common/`): response envelope, exception handling with stable error codes, pagination/filter/order helpers, strict serializers, model mixins (timestamps, soft delete, cache), request-id logging, Sentry hook, throttling (including per-workspace), file storage (R2/local/in-memory), Fernet encryption helper, `/api/health/`.

v1 (backend only, no AI/RAG) is mapped in [backend/Project.MD](backend/Project.MD). Build order: accounts and sessions, audit log, workspaces, knowledge base, tickets and portal, Gmail and email, dashboard. The `ai` app (full-text search, Gemini) comes after.

Quick start:

```bash
cd backend
cp .env.example .env        # fill in the values
docker compose up -d        # Postgres (ParadeDB image) + Redis (or `docker compose up --build` for the API too, with hot reload)
uv sync
uv run python manage.py migrate
uv run python manage.py runserver
uv run python manage.py test
```

Backend conventions, guardrails and confirmed product decisions are in `backend/CLAUDE.md`. Every meaningful change is logged in `backend/DECISION.md`; code paths are traced in `backend/FLOW.md`.

API requests are kept in `backend/postman/` (collection and environment), updated with every API change.

## Frontend

Built in `frontend/` (React 19, Vite, TanStack, Tailwind v4, Base UI): dashboard, tickets with assignment, knowledge base with a category graph view (`@xyflow/react`), members and invitations, settings, audit log, Gmail, public portal. All tables use one chip filter bar. See [frontend/README.md](frontend/README.md) and [frontend/PROJECT.md](frontend/PROJECT.md).

## Key product decisions

- Google-only sign-in; OWNER and MEMBER roles; RBAC permissions plus fixed ABAC rules.
- RESOLVED and CLOSED are separate ticket states; only the owner reopens CLOSED.
- Customers follow tickets by email only; internal notes never reach customers.
- Knowledge base: in-app articles plus PDF/TXT uploads, 50 MB per workspace.
- AI never sends or changes anything on its own; answers cite real retrieved articles.

Open points are tracked in section 14 of the LLD.
