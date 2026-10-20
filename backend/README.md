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
- Feature apps are added one at a time (see the root README)

Docs: `Project.MD` (v1 feature map and build order), `CLAUDE.md` (rules), `DECISION.md` (decision log), `FLOW.md` (code paths).
