# ResolveAI frontend

React + TypeScript single-page app for ResolveAI, the support desk where customers file tickets through a workspace portal and agents answer them. It talks to the Django API in `../backend` using the session cookie (Google sign-in, no tokens in the browser).

## Status

Scaffold and reusable component library done. The library is previewed live at `/design-preview` (and `/design-preview/frame` for the app frame); it awaits approval, and feature screens start after it is approved. See [PROJECT.md](PROJECT.md).

## Stack

- Vite 8, React 19, TypeScript (strict)
- TanStack Router (file-based routes), Query (server state), Table (data grids)
- Tailwind CSS v4 + shadcn/ui (`base-nova` style on Base UI), Phosphor icons, GSAP for motion
- Forms: library not chosen yet (see DECISION.md)
- ESLint, Prettier, Vitest + Testing Library
- Package manager: pnpm

## Run it

```bash
pnpm install
cp .env.example .env      # optional; sets where /api is proxied
pnpm dev                  # http://localhost:3000, /api proxied to the backend (default http://localhost:8000)
```

| Command | What it does |
| --- | --- |
| `pnpm dev` | Dev server with hot reload |
| `pnpm build` | Production build, then type check |
| `pnpm lint` | ESLint |
| `pnpm format` | Prettier |
| `pnpm test` | Vitest (single run); `pnpm test:watch` to watch |

Start the backend first (`../backend/README.md`). The Vite proxy keeps API calls same-origin so the session and CSRF cookies work without extra CORS setup.

The browser always calls the dev server's own origin (for example `http://localhost:3000/api/health/`); Vite forwards `/api` to `VITE_API_PROXY_TARGET`. Seeing `localhost:3000/api/...` in the network tab is expected. A 404 there means the backend has no such route yet: `/api/health/` exists today, the Google sign-in routes arrive with the backend's account feature.

## Docker

```bash
docker compose up --build                               # dev: http://localhost:3000, source bind-mounted, hot reload
docker compose -f docker-compose.prod.yml up --build -d # static build behind nginx, no bind mount
```

Inside a container `localhost` is the container itself, so the compose files send `/api` to `http://host.docker.internal:8000` (the backend's published port). Point it elsewhere with `FRONTEND_API_PROXY_TARGET` in `.env` or the shell, for example `http://api:8000` when both stacks share a Docker network. `node_modules` lives in a named volume: after changing dependencies run `docker compose up --build` and, if the old packages linger, `docker compose down -v` first. On Linux with working file events, set `VITE_USE_POLLING=false`.

## Layout

```
src/
  routes/               TanStack Router file routes (routeTree.gen.ts is generated and committed)
  features/<name>/      one folder per feature: api.ts (Query hooks), components, schemas
  components/ui/        shadcn primitives (Base UI; edit sparingly)
  components/patterns/  our reusable components: DataTable, StatCard, ticket badges, filters
  components/layout/    AppShell (icon rail, top bar)
  motion/               GSAP helpers: useReveal, CountUp, useFlip, icon hover motion
  icons/                the only place Phosphor icons are imported from
  styles/tokens.css     design tokens (light and dark)
  hooks/  lib/          shared hooks; api client, utils, query client
  test/                 Vitest setup
```

`/design-preview` is the living catalogue of the reusable components and `/design-preview/frame` shows the full app frame. Add every new reusable component there.

## Docs

- [PROJECT.md](PROJECT.md): scope, conventions, status
- [DECISION.md](DECISION.md): append-only decision log
- [FLOW.md](FLOW.md): how data and code travel through the app
- [CLAUDE.md](CLAUDE.md): working rules, including the impeccable-skill design rule
- [PRODUCT.md](PRODUCT.md) and [DESIGN.md](DESIGN.md): product record and design system draft (impeccable format)

## Adding a shadcn component

The shadcn CLI could not reach its registry from the build environment, so the first set of primitives was copied from the shadcn source repository. On a normal machine `pnpm dlx shadcn@latest add <component>` works with the committed `components.json`.

## Install troubleshooting

If `pnpm install` fails with `ERR_PNPM_MINIMUM_RELEASE_AGE_VIOLATION`, your pnpm blocks very new releases and the lockfile pins one. Run `pnpm clean --lockfile && pnpm install` to re-resolve under your policy.
