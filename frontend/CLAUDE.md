# CLAUDE.md (frontend)

Guidance for working in `resolve-ai/frontend`. Read PROJECT.md, DECISION.md, FLOW.md and DESIGN.md first.

## Design rule (owner instruction, 2026-10-20)

**Every frontend change that touches UI, styling, layout, motion or copy must take its reference from the `impeccable` skill.** Load/invoke it before drafting or changing a design, component, screen or the design system, and follow its guidance alongside `DESIGN.md`. If the skill is not available in the session, say so and ask the owner for it instead of skipping the step. Source: github.com/pbakaus/impeccable (`npx impeccable install`; in cloud sessions where it cannot be installed, read `plugin/skills/impeccable/SKILL.md` and its `reference/` files from raw.githubusercontent.com). `PRODUCT.md` and `DESIGN.md` are the project context it reads; keep them current.

## Working rules

- Stack and conventions: see PROJECT.md. Decisions are append-only in DECISION.md; call paths live in FLOW.md.
- Icons come from `@/icons` (Phosphor); motion from `src/motion` (GSAP); respect reduced motion.
- Use design tokens (CSS variables) and the `Tone` type; never hard-code colors.
- Server data only through TanStack Query hooks over `src/lib/api.ts`.
- New reusable components get a section entry in `/design-preview` (`src/features/design-preview`).
- Before finishing: `pnpm build`, `pnpm lint`, `pnpm test`.
- Do not implement feature screens until the design system is approved.
