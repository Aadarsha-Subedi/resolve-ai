# PROJECT.md

Frontend scope, conventions and status. The product itself is described in `../backend/docs/ResolveAI_LLD.md` and `../backend/Project.MD`.

## Goal

A fast, accessible web app for agents and workspace owners, plus the public customer portal, on top of the Django API. Look and feel follow the reference UI (soft light theme, yellow primary, dense data tables, status badges); the design system is the source of truth once approved.

## Scope (v1, mirrors the backend)

Accounts and sessions, audit log, workspaces, knowledge base, tickets and portal, Gmail connection and email, dashboard. AI/RAG screens are deferred, like the backend.

## Status

| Area | State |
| --- | --- |
| Scaffold (Vite, React, TS, TanStack, Tailwind) | Done |
| shadcn primitives (base-nova, Base UI) | Done, 35 components |
| Reusable components | Done: DataTable, StatCard, ticket badges, filters, PageHeader, ConfirmDialog, AppShell, ThemeToggle and more, with a live preview at `/design-preview` |
| API client and auth query | Done; uses the backend's `/api/me/`, `/api/csrf/` and `/api/auth/google/start/` |
| Design system | Component library and tokens built, awaiting owner approval |
| Public pages | Landing, sign in, sign up, terms, privacy drafted (UI only; legal text is a draft) |
| Feature screens | Not started |

## Conventions

- Feature code lives in `src/features/<name>`; routes stay thin and compose feature components.
- All server data goes through TanStack Query hooks that call `lib/api.ts`. No `fetch` in components.
- Never hard-code colors in components; use design tokens (CSS variables) and the `Tone` type for status colors.
- Forms: library undecided; use the shadcn field components until chosen.
- Icons only via `@/icons`; motion only via `src/motion`.
- Tables: `DataTable` in `components/patterns` (TanStack Table v9). Columns and data must be referentially stable.
- Authorization is enforced by the backend; the UI only hides what the user cannot do.
- Every new reusable component is added to `/design-preview`.
- Update DECISION.md for meaningful decisions and FLOW.md when a call path changes.

## Backend contract the UI relies on

Response envelope `{success, status_code, message, data, meta}` (errors add `code` and `errors`), trailing-slash routes under `/api`, session cookie plus `X-CSRFToken` on writes, Google sign-in by full-page redirect, non-members get 404 on workspace data.
