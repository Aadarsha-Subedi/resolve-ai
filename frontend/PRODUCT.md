# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

React 19 + TypeScript (Vite), TanStack Router/Query/Table, Tailwind v4 + shadcn/ui, Phosphor icons, GSAP. Backend is a separate Django API (`../backend`). Decided by the owner; see DECISION.md.

## Users

- **Agents** (and workspace owners) working a queue of customer tickets all day, mostly on desktop, scanning many rows and replying by email from their own Gmail.
- **Workspace owners** who also configure the workspace, members, knowledge base, Gmail connection and portal, and read the dashboard.
- **Customers** who submit a ticket through a public workspace portal (a short, separate surface; follow-up is by email, not a customer login).

## Product Purpose

ResolveAI is a multi-tenant support desk: customers file tickets through a workspace portal, agents resolve them with Gmail-based email, and (later) AI drafts replies grounded in the workspace knowledge base; a human always reviews and sends. Success is tickets resolved faster with nothing lost between email and the desk. A capstone project, so it must demonstrate real engineering and design quality.

## Positioning

Not decided. Candidate to confirm: AI drafts, a human always sends, grounded in the workspace's own knowledge base. (AI is deferred in v1.)

## Operating Context

Operate mode: the agent is in a task, usually with the ticket list open for hours. Tickets arrive from email (Gmail Pub/Sub push plus a manual "sync latest mails") and the portal. Sessions are Google sign-in with server-side Django sessions. Workspace is the tenant; non-members see 404.

## Capabilities and Constraints

- v1 scope: accounts and sessions, audit log, workspaces, knowledge base, tickets and portal, Gmail connection and email, dashboard. AI/RAG screens deferred.
- Ticket statuses Open, Pending, Resolved, Closed (Closed reopened only by the owner); priorities Urgent, High, Medium, Low; fixed categories Billing, Technical, Account, Feature request, General, Other; channels Email, Chat, Slack as shown in the reference (to confirm against the backend).
- "Health" (On Track, Warning, Breached) in the reference is assumed SLA-driven; not confirmed.
- Authorization lives in the backend (RBAC plus fixed ABAC rules); the UI hides what the user cannot do.
- Response envelope and trailing-slash routes; see PROJECT.md.

## Brand Commitments

- Reference UI image supplied by the owner (Tickets screen): yellow primary action, soft neutral surfaces, dense table, soft status badges. It is binding for look and layout.
- Fonts: Anthropic Sans (Text and Display), licensed files supplied by the owner.
- Icons: Phosphor. Motion: GSAP, subtle, including on icon hover.
- Name: ResolveAI. No logo asset yet (the reference shows a yellow tile with a mark).

## Evidence on Hand

- Reference image: `/mnt/project-files/resolve-ai/` upload `resolve-ai-ui-reference.jpg` (Tickets screen).
- Backend docs: `../backend/docs/ResolveAI_LLD.md`, `../backend/Project.MD`.
- No real tickets, customer content, testimonials or logos exist; sample data in the UI must be clearly fake and never presented as real.

## Product Principles

1. The queue is the product: lists scan fast, status is legible at a glance, and nothing needs a click to be understood.
2. Familiar over clever: standard patterns in a calm tool that disappears into the task.
3. A human is always in the loop: sending, closing and destructive actions are explicit and reversible where possible.
4. Color means status; the yellow accent marks the one primary action.
5. Errors name the problem and the recovery.

## Accessibility & Inclusion

Target WCAG 2.2 AA: keyboard operable everywhere, visible focus, 4.5:1 text contrast, status never conveyed by color alone, reduced-motion respected. Product-specific needs not yet gathered.
