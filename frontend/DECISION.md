# DECISION.md

Log of meaningful decisions that change the codebase. Append only; supersede with a new entry instead of editing old ones.

Format: **Date, title** / Decision / Reason / Alternatives / Files.

---

## 2026-10-20, Stack and tooling
- **Decision:** pnpm, Vite + React 19 + strict TypeScript, TanStack Router (file-based), Query and Table, Tailwind v4 with shadcn/ui (Radix, new-york), React Hook Form + Zod, ESLint + Prettier, Vitest + Testing Library.
- **Reason:** owner approved the proposed list on 2026-10-20. Router and Table are type-safe and headless, which suits a data-heavy ticket UI; shadcn gives owned, themeable components.
- **Alternatives:** Next.js (rejected: the backend is separate, no SSR need), Redux/Zustand for server data (rejected: Query covers it), Storybook (rejected: a `/design` route is enough for now).
- **Files:** `package.json`, `vite.config.ts`, `eslint.config.js`.

## 2026-10-20, Auth via session cookie and backend Google redirect
- **Decision:** no tokens in the browser. Sign-in is a full-page redirect to the backend's Google login URL; the app loads the current user on start, treats 401/403 as signed out, and sends `X-CSRFToken` (from the `csrftoken` cookie) on writes. Dev proxies `/api` through Vite.
- **Reason:** matches the backend decision (allauth code flow, Lax cookie). Same-origin proxy avoids CORS and cookie edge cases.
- **Files:** `src/lib/api.ts`, `src/features/auth/api.ts`, `vite.config.ts`.

## 2026-10-20, shadcn primitives copied from source, not via the CLI
- **Decision:** the primitives in `src/components/ui` were copied from the `new-york-v4` sources in the shadcn-ui repository, with imports rewritten to our aliases, and `components.json` written by hand. `next-themes` was replaced by our own `ThemeProvider`; `use-mobile` and the sidebar skeleton were adjusted to satisfy React lint rules.
- **Reason:** the build environment could not reach `ui.shadcn.com` (blocked), so `shadcn init` failed. The output matches what the CLI produces for this style.
- **Alternatives:** wait for network access (rejected: blocks the work). On a normal machine the CLI works with `components.json`.
- **Files:** `components.json`, `src/components/ui/**`, `src/components/theme-provider.tsx`, `src/hooks/use-mobile.ts`.

## 2026-10-20, TanStack Table v9 API
- **Decision:** `DataTable` uses v9 (`useTable`, explicit `tableFeatures`), not the v8 `useReactTable`.
- **Reason:** v9 is the current release; features are opt-in so bundle and state stay small. Features and columns must be stable references.
- **Files:** `src/components/common/data-table.tsx`.

## 2026-10-20, Build order is vite then tsc
- **Decision:** `pnpm build` runs `vite build && tsc -b`.
- **Reason:** the router plugin generates `routeTree.gen.ts` during Vite startup; type checking before it exists fails on a clean checkout. The generated file is also committed.
- **Files:** `package.json`.

## 2026-10-20, Provisional design tokens
- **Decision:** `src/index.css` holds neutral placeholder tokens until the design system is approved; no feature work before then.
- **Reason:** owner wants the design system finalized before implementation.
- **Files:** `src/index.css`.

## 2026-10-20, Icons, motion and font choices (design system draft)
- **Decision:** Phosphor icons, GSAP for motion, Anthropic Sans as the primary font (Display Regular only, woff2 in `public/fonts/`, Inter fallback).
- **Reason:** owner's choices. Icon and motion changes are applied after the design system is approved; only the font face and `--font-sans` are wired now.
- **Files:** `DESIGN.md`, `src/index.css`, `public/fonts/`.

## 2026-10-20, Frontend design work references the impeccable skill
- **Decision:** `CLAUDE.md` requires every UI change to take reference from the `impeccable` skill.
- **Reason:** owner instruction. The skill (github.com/pbakaus/impeccable, v4.7.0) could not be installed in the cloud session, so its reference files were read directly. The design system was redrafted against it as `DESIGN.md` (impeccable's format, with `PRODUCT.md`). Operate-mode rules replaced the earlier page-entrance and count-up animations; the launcher and detector have not been run.
- **Files:** `CLAUDE.md`.

## 2026-10-20, Component library rebuilt on base-nova (Base UI) with a live preview
- **Decision:** the earlier Radix `new-york` primitives and the markdown-only design draft were replaced. `src/components/ui` now follows the owner's `project-management` library (shadcn `base-nova` on Base UI), with Phosphor icons through `@/icons`, GSAP helpers in `src/motion` (reveal, count-up, flip, icon hover motion; reduced motion and touch turn them off), and tokens in `src/styles/tokens.css` (yellow primary, tinted neutrals, soft status tones). A `/design-preview` route and an app-frame preview replace `/design`. `react-hook-form`, `zod`, `lucide-react` and `radix-ui` were removed; the form library is undecided. `typescript` is pinned to 6.0.x because typescript-eslint does not support 7.
- **Reason:** owner said the design system meant a working reusable component library with a live preview like `project-management`, drafted before any page. This supersedes the 'shadcn primitives copied from source' and 'Provisional design tokens' entries and the stack entry's Radix and form-library parts.
- **Alternatives:** keeping Radix (rejected: owner's reference library uses Base UI).
- **Files:** `components.json`, `src/components/**`, `src/motion/**`, `src/styles/tokens.css`, `src/features/design-preview/**`, `package.json`.

## 2026-10-20, Design review round 1
- **Decision:** status and health badges always carry a filled icon in the same hue (no dots). Buttons get a premium finish (top highlight, soft shadow, border tint) and their icons ease on hover through CSS in `Button`; icon-only buttons scale slightly. Dropdown options carry icons (`OptionSelect`, `FilterSelect`); a filter shows its name until set, then only the chosen option, with no `Filter: Option` prefix. `StatCard` is one flat tile (the reference's nested panel is dropped). Shortcuts render as key caps via `Shortcut`/`Kbd` in menus, the command palette and a Keyboard shortcuts dialog on a plain surface.
- **Reason:** owner feedback on the first preview. Supersedes keeping the stat card's nested form per the reference.
- **Files:** `src/components/patterns/{ticket-meta,option-select,filter-select,stat-card}.tsx`, `src/components/ui/{button,kbd,command,dropdown-menu}.tsx`, `src/features/design-preview/sections/*`.

## 2026-10-20, Pill buttons and hover border gradient reverted
- **Decision:** the pill button with a sliding icon chip and the Aceternity-style hover border gradient were tried and removed on the owner's request. `Button` is back to the round-one design: rounded-lg, premium finish (top highlight, soft shadow, tinted border), icons that ease up or nudge on hover through CSS. `--ctl-h` is back to 32px. All six review-round-1 changes stay.
- **Reason:** owner: 'Revert all the button changes... go back to your initial draft.'
- **Files:** `src/components/ui/button.tsx`, `src/styles/tokens.css`, `src/index.css`, `src/features/design-preview/sections/actions.tsx`.

## 2026-10-20, Chip buttons restored with calmer contrast and slower motion
- **Decision:** the sliding-chip pill `Button` is back (owner prefers it; the earlier revert is superseded). The chip is now a soft tint of the button's own ink (translucent white on yellow, a faint foreground tint elsewhere, destructive tint on destructive) instead of an inverse black chip, so label and icon share one hue. The glide runs 700ms on an in-out curve (was 400ms expo-out). `--ctl-h` is 36px again. The command palette now uses the same dialog layout as the Keyboard shortcuts dialog: visible title and description, spaced groups, 36px rows, key-cap shortcuts; cmdk's selected-row style keys off `data-selected=true` so only the active row highlights.
- **Files:** `src/components/ui/button.tsx`, `src/components/ui/command.tsx`, `src/styles/tokens.css`, `src/features/design-preview/sections/{actions,menus}.tsx`.

## 2026-10-20, Black primary button experiment
- **Decision:** `default` Button is now ink (black, white label and icon) and the chip has no background of its own, so button, label and icon read as one surface; the icon still glides across on hover. The yellow button remains as the `accent` variant. In dark mode `default` inverts (light button, dark label). Glide shortened from 700ms to 500ms.
- **Reason:** owner asked to experiment with a black primary and no separate icon background, and for a faster animation. Easy to flip back by swapping the `default` and `accent` classes.
- **Files:** `src/components/ui/button.tsx`, `src/features/design-preview/sections/actions.tsx`.

## 2026-10-20, Tighter icon-to-label gap on chip buttons
- **Decision:** the resting gap between label and icon is now 6px of padding (was 14px), and the hover offset matches, so icon and label read as one unit.
- **Files:** `src/components/ui/button.tsx`.

## 2026-10-20, Yellow chip button is the default; public pages drafted
- **Decision:** the black experiment is dropped. `default` Button is the yellow chip button (no `accent` variant). `Button` sets `nativeButton={false}` automatically when given `render` (links as buttons). Public pages drafted as Persuade-mode surfaces under `src/features/marketing`: landing at `/`, `/login`, `/signup`, `/terms`, `/privacy`. Sign-in and sign-up are both the backend's Google redirect (`googleLoginUrl`), so the two pages differ only in copy; there is no email/password form because the backend has none. Terms and Privacy are drafts written from how the product works, with bracketed placeholders and a visible 'Draft, not yet reviewed by a lawyer' notice. Landing headlines use Display type (marketing titles), the one place beyond app page titles. The yellow band is the page's committed colour field; one authored motion moment (hero queue rows settle in). Product fragments are sample data, decorative and `aria-hidden`.
- **Reason:** owner asked for the yellow chip look as default and a landing page with sign-up, log-in, terms and privacy. Impeccable Persuade rules applied: no eyebrows, no icon-card grid, no nested cards, no gradient text.
- **Files:** `src/components/ui/button.tsx`, `src/features/marketing/**`, `src/routes/{index,login,signup,terms,privacy}.tsx`.

## 2026-10-20, Docker setup and dev server port
- **Decision:** `Dockerfile.dev` and `docker-compose.yml` run Vite with the source bind-mounted (node_modules in a named volume, polling on by default for Docker Desktop); `Dockerfile.prod`, `nginx.conf.template` and `docker-compose.prod.yml` serve the static build with nginx, which proxies `/api` to `API_UPSTREAM`. The proxy target inside containers is `http://host.docker.internal:8000` (override with `FRONTEND_API_PROXY_TARGET`). The dev server now listens on port 3000 on all interfaces, matching the backend's `FRONTEND_URL`, CORS and CSRF origins. `vite.config.ts` reads `.env` through `loadEnv`, because Vite does not put `.env` values in `process.env` for the config file; a shell variable still wins.
- **Reason:** owner asked to dockerize with hot reload and reported the API proxy target being ignored. The `localhost:3000/api` URL itself is correct (same-origin proxy); the real 404 is the backend not having Google login routes yet (`/api/health/` is its only route).
- **Files:** `Dockerfile.dev`, `Dockerfile.prod`, `docker-compose.yml`, `docker-compose.prod.yml`, `nginx.conf.template`, `.dockerignore`, `.env.example`, `vite.config.ts`, `README.md`.

- **Decision (sign-in endpoints):** the frontend now uses the backend's real routes: `GET /api/auth/google/start/?remember=0|1&next=` to sign in, `/api/me/` for the profile, `/api/csrf/` to seed the CSRF cookie. The earlier 404 on `/api/auth/google/login/` was a wrong path in the frontend, not the proxy. Google errors arrive as `/login?google_error=<code>` and render as an alert. Google Console redirect URI must be `http://localhost:3000/api/auth/google/login/callback/` when going through the proxy.
