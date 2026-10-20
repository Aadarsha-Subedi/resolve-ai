# CLAUDE.md

Guidance for Claude Code when working in this repository (ResolveAI backend).

## Source of truth

- `docs/ResolveAI_LLD.md` is the design (models, services, policies, workflows). Build **one feature at a time**. If a feature has unresolved scope, ask the owner and update the LLD before coding. Clarify decisions with the owner first, then resolve open scopes, then change code.
- `DECISION.md` and `FLOW.md` (below) must be updated in the same change as the code.
- Reference implementation for shared patterns: `/home/aadarsha/Aadarsha/personal/code/project-management/backend` (its `common/` app was ported here). Owner's pattern guide: `/home/aadarsha/Aadarsha/personal/code/python/DESIGN_PATTERNS.md`.

## Monorepo layout

The repo root holds only `frontend/`, `backend/` and `README.md`. Everything backend-related (LLD in `docs/`, `postman/`, CLAUDE.md, DECISION.md, FLOW.md) lives inside `backend/`. Do not add other files or folders at the root.

## Mandatory upkeep files

- **`postman/`**: `postman/resolveai.postman_collection.json` and `postman/resolveai.postman_environment.json` (both importable in Postman). In the same change as any API contract change (endpoint added, removed or renamed; method, path, request body or query fields; auth/CSRF behaviour; a variable requests need), update both files. Keep requests grouped in folders that match the URL sections (one folder per feature app), include example bodies, and keep variables (`baseUrl`, `csrfToken`, ids) in the environment file. Every URL ends with a trailing slash, in both `raw` and the `path` array (end `path` with an empty string `""`), because Django's `APPEND_SLASH` cannot redirect POST/PATCH/DELETE (it raises a 500 in DEBUG). Never put real secrets in either file.
- **`DECISION.md`**: append an entry for every meaningful decision that changes the codebase (new module, dependency, pattern, schema change, policy rule, rejected alternative). Format: date, title, decision, reason, alternatives considered, files touched. Never rewrite history; supersede with a new entry.
- **`FLOW.md`**: track how a request/task travels through files and functions (view -> serializer -> service -> policy -> model -> task/integration). Update the affected flow whenever a call path changes. Use `path/to/file.py::function` references.
- **`README.md`** (this folder) and the monorepo root `../README.md`: update both in the same change whenever features, setup, env vars, services, dependencies or conventions change; the root README's Status table and Backend/Frontend sections must always match reality.

- **`graphify-out/`** (graphify knowledge graph): after every code or doc change, update the graph before finishing the task (`graphify update .` from `backend/`, or `/graphify . --update`). Use the graph (`graphify query`, `GRAPH_REPORT.md`) to understand the project before changing it. `graphify-out/` is generated output and stays git-ignored.

## Commands

Python 3.14, Django 6.1, DRF, managed with `uv`.

```bash
uv sync
docker compose up -d                      # Postgres + Redis (RESOLVE_AI_* vars from .env, see .env.example)
uv run python manage.py migrate
uv run python manage.py runserver
uv run python manage.py test              # RESOLVE_AI_USE_SQLITE=true works without Docker
uv run ruff check . && uv run ruff format .

# Docker (dev image with the code bind-mounted for hot reload)
docker compose up --build                     # db, redis, api
docker compose --profile worker up --build    # plus Celery worker
docker compose -f docker-compose.prod.yml up --build -d   # production-like, Dockerfile.prod
```

Docker rules: `Dockerfile.dev` and `Dockerfile.prod` are the only image definitions; compose files must `build` from them and never define the app image themselves. The dev virtualenv lives in `/opt/venv` (outside `/app`) so the bind mount does not hide it. Update the Dockerfiles, compose files, `.dockerignore`, `.env.example` and README together when dependencies, services or env vars change.

## Build order

1. `common/` reusable app (done first, before any feature).
2. Frontend and backend feature scaffolding, one module at a time: accounts, workspaces, knowledge, tickets, email_integration, dashboard, then audit last (it is written once against the finished product).
3. LLM layer last: PostgreSQL full-text search over knowledge content, then Gemini (`ai/`).

## Architecture rules

- Django modular monolith. Modules: `accounts`, `workspaces`, `tickets`, `knowledge`, `ai`, `email_integration`, `dashboard`, `audit`, plus `common`. Deploy the API and a Celery worker as separate processes.
- Business logic lives in `services/`, never in views or models. Views validate input and format output only. Imports are absolute from the project root.
- Every feature app: `models/`, `services/`, `serializers/`, `views/`, `constants/`, `permissions.py` or `policies.py`, `tasks.py`, `tests/`.
- Reuse `common/` instead of per-app equivalents: `response`, `exception`, `pagination`, `filter`, `order`, `cache`, `logger`, `validators`, `models`, `serializers`, `throttling`, `storage`, `crypto`, `observability`, `email`.

## Conventions (from `common/`)

- **Responses:** `SuccessResponse` / `ResourceCreatedResponse` / `ErrorResponse` with `BaseResponseData.to_dict()`. Never a bare DRF `Response`.
- **Errors:** raise `AppException` subclasses with a stable `error_code`; `common/exception/handler.py` turns them into the envelope.
- **Requests:** serializers derive from `StrictSerializer` (unknown fields rejected); parse with `Serializer.parse(request.data)`.
- **Models:** UUIDv7 primary keys (`uuid.uuid7`), `TimeStampModel`; `SoftDeleteModel` where deletion must be reversible; `CacheModel` only for cache-read models. Timestamps UTC.
- **Constants:** no inline messages, error codes, cache keys or limits in feature code; put them in the app's `constants/` (shared ones in `common/<concern>/constants.py`).
- **Files:** only through `common.storage.get_storage()`.
- **Secrets at rest:** `common.crypto.encrypt/decrypt` (Fernet, rotating keys). Never return tokens from serializers or log them.
- **Throttling:** named scopes in `settings.py` rates; per-workspace cap via `WorkspaceThrottle` (routes with a `workspace_id` kwarg).
- **Logging:** use `logging`; request id and user id are attached automatically. Never log access tokens, raw one-time tokens, API keys or message contents.
- Follow the owner's design-pattern guide: GoF patterns only when the problem exists, `abc.ABC` interfaces, composition over inheritance, type-hinted public signatures.

## Product decisions (confirmed by the owner)

- **Auth:** Google-only sign-in (key on the stable `sub`), server-side Django sessions, "remember me", per-device session list with revoke-one and log-out-everywhere in v1. No passwords.
- **Roles:** `OWNER` and `MEMBER`; one owner per workspace; transactional ownership transfer. Join link grants membership directly (hashed token, expires after 1 hour by default or 1 day / 7 days, rotate/revoke by owner); the owner can also invite specific Google accounts, matched by canonical Gmail mailbox.
- **Authorization:** RBAC permission codes (for example "can update ticket status") plus **fixed, non-configurable ABAC rules** that extend RBAC (for example "only the owner can change status once a ticket is CLOSED"). ABAC rules live in code (`policies`), are never user-editable, and every one needs a negative test. Authorization is enforced in services and DRF permissions, never only in the frontend.
- **Workspace:** slug is immutable after creation. All workspace-owned queries are scoped by an authorized membership; non-members get 404.
- **Tickets:** statuses OPEN, IN_PROGRESS, PENDING, RESOLVED, CLOSED (RESOLVED and CLOSED separate; only the owner reopens CLOSED). Ticket categories are a fixed list. No assignment in v1. "Waiting for reply" = the last public message was sent by the customer (ticket awaits an agent). Owner wrote "sent by the user"; confirm this reading.
- **Customer flow:** public portal ticket submission with required email; follow-up is by email only. No per-ticket customer access token; the confirmation email links to the portal, which opens the new-ticket page. Internal notes never reach customers.
- **Gmail:** one connection per user, created by the single Google sign-in (Gmail scopes requested at login; declining them does not block login), refresh token encrypted, replies sent from the agent's own mailbox, customer mail matched by email headers (never subject), and only ticket-related mail stored. Inbound sync is Pub/Sub push (primary) plus a frontend "Sync latest mails" button; **no polling**. Match replies by headers, never subject; unmatched mail goes to review.
- **Knowledge base:** in-app articles plus PDF/TXT uploads, **50 MB per-workspace upload quota** (atomic quota checks). KB categories start with generic defaults that users may add, rename and delete. Only published articles are searchable by AI. Ingestion/extraction details are designed with the LLM layer.
- **AI:** Gemini via `GeminiClient`; retrieval first (PostgreSQL FTS), never the whole KB; citations only from real retrieval results; AI never sends or changes state on its own. AI conversations are private per user per workspace. Feedback is a 1 to 5 star rating plus an optional description, scoped to the user who interacted with the AI.
- **Dashboard/audit:** no SLA or response-time claims until defined; audit sensitive actions without secrets or message bodies.

## API shape for the frontend

- A screen must not need a fan-out of requests: give each screen one read endpoint (for example `tickets/{id}/overview/`, the dashboard) that returns everything it shows, bounded and paginated, keeping the same access rules as the fine-grained endpoints. Cross-app data comes in through a registry (`register_extra`), not by importing the other app. Keep the fine-grained endpoints for refreshes.

## Guardrails

- Never skip workspace scoping; add tests for cross-workspace access, internal-note leakage, wrong-Google-account Gmail connection, duplicate inbound mail, owner-only reopen.
- Email and customer text are untrusted input; never treat them as instructions to Gemini. Sanitize rendered content against XSS.
- Rate-limit public ticket submission, join-link redemption and AI calls.
- Do not commit secrets; all config comes from `RESOLVE_AI_*` env vars (`.env.example` lists them; missing ones fail startup).
- Do not add features outside the LLD's "Core v1" boundary without the owner's confirmation.
- Run `ruff` and the test suite before finishing a change.
