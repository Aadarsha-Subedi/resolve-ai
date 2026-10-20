---
name: ResolveAI
description: A calm, dense support desk where one yellow action leads and color means status.
colors:
  primary: "#FFC800"
  on-primary: "#1A1916"
  ink: "#1A1916"
  ink-muted: "#6E6B63"
  canvas: "#FFFFFF"
  panel: "#F7F6F3"
  line: "#E9E7E2"
  status-info-bg: "#E0EEFF"
  status-info-fg: "#1D4ED8"
  status-warning-bg: "#FEF3C7"
  status-warning-fg: "#92400E"
  status-danger-bg: "#FEE2E2"
  status-danger-fg: "#B91C1C"
  status-success-bg: "#DCFCE7"
  status-success-fg: "#166534"
  status-neutral-bg: "#EFEDE8"
  status-neutral-fg: "#55524A"
  destructive: "#DC2626"
  canvas-dark: "#121110"
  card-dark: "#1A1917"
  panel-dark: "#242321"
  line-dark: "#2E2C29"
  ink-dark: "#F3F1EC"
  ink-muted-dark: "#A29E94"
typography:
  page-title:
    fontFamily: "Anthropic Sans Display, Anthropic Sans, Inter, system-ui, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 600
    lineHeight: 1.33
    letterSpacing: "-0.01em"
  section-title:
    fontFamily: "Anthropic Sans, Inter, system-ui, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 600
    lineHeight: 1.45
  body:
    fontFamily: "Anthropic Sans, Inter, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.45
  table-cell:
    fontFamily: "Anthropic Sans, Inter, system-ui, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Anthropic Sans, Inter, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 500
    lineHeight: 1.33
  stat:
    fontFamily: "Anthropic Sans, Inter, system-ui, sans-serif"
    fontSize: "1.75rem"
    fontWeight: 600
    lineHeight: 1.2
rounded:
  badge: "6px"
  control: "8px"
  panel: "12px"
  ring: "16px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.control}"
    padding: "0 16px"
    height: "36px"
  button-outline:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "0 12px"
    height: "36px"
  input:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    height: "36px"
  badge:
    rounded: "{rounded.badge}"
    padding: "2px 8px"
  table-header:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink-muted}"
    height: "36px"
  table-row:
    height: "40px"
---

# Design System: ResolveAI

Status: implemented as `src/styles/tokens.css` and the component library, previewed at `/design-preview`; awaiting owner approval. Authored against the reference Tickets screen and the impeccable skill (Operate mode). Companion: PRODUCT.md.

## Overview

**Creative North Star: "The Well-Run Desk"**

A tidy working desk at the start of a shift: everything within reach, nothing shouting. The interface is a tool that disappears into the task of working a queue. Surfaces are quiet and warm-neutral, density is high, and the only loud thing on any screen is the one yellow action that moves work forward.

Operate mode governs: scanability, consistency and familiar patterns outrank expression. Personality lives in precise details (the yellow, the tinted neutrals, tabular numerals, considered icon motion), not in decoration. The reference image is binding for layout and look; impeccable informs everything it does not decide.

**Key Characteristics:**
- Warm-tinted neutrals (never pure gray), one saturated accent, soft tinted status badges.
- Dense tables, flat surfaces, borders before shadows.
- Motion explains state and feedback; it is never a page-load show.
- One type family does the work; Display appears only on page titles.

## Colors

Restrained palette: tinted neutrals carry 90%+ of the surface, yellow marks the single primary action, and hue is otherwise reserved for status.

### Primary
- **Signal Yellow** (#FFC800): the primary button, the logo tile, selected-row and active-state accents, text-selection tint. Always with **Ink** text on top (white on yellow fails contrast).

### Neutral
- **Ink** (#1A1916 light / #F3F1EC dark): body text, headings, icons at rest.
- **Ink Muted** (#6E6B63 / #A29E94): secondary text, labels, table headers, placeholders. Tinted from the neutral hue, never a cool gray.
- **Canvas** (#FFFFFF / #121110): app background and table body.
- **Panel** (#F7F6F3 / #242321): the second neutral layer: table header, sidebar, stat-card outer ring, hover fill.
- **Card** (#FFFFFF / #1A1917): popovers and raised surfaces.
- **Line** (#E9E7E2 / #2E2C29): hairlines and input borders.

### Status tones
Soft badges: tinted background, strong foreground of the same hue (each pair is at least 4.5:1; verify with the detector/contrast check when built).

| Tone | Background / text (light) | Used for |
| --- | --- | --- |
| Info | #E0EEFF / #1D4ED8 | Open |
| Warning | #FEF3C7 / #92400E | Pending, health Warning |
| Danger | #FEE2E2 / #B91C1C | Breached, errors |
| Success | #DCFCE7 / #166534 | Resolved, positive trend |
| Neutral | #EFEDE8 / #55524A | Closed, On Track |

Dark mode uses the same hues at about 15% alpha backgrounds with lightened foregrounds. Destructive actions use #DC2626 (dark: #F87171).

### Named Rules
**The One Voice Rule.** Yellow is used on at most one primary action per screen plus quiet state accents; it never fills large areas and never appears on inactive controls.
**The Meaning Rule.** Hue means status. Every status also carries an icon or label, so color is never the only signal.
**The Tinted Neutral Rule.** No pure gray and no pure black text; every neutral leans slightly warm, including secondary text.

## Typography

**Primary Font:** Anthropic Sans, Text cut (Regular 400, Medium 500, Semibold 600), fallback Inter, system-ui, sans-serif.
**Display Font:** Anthropic Sans Display (Regular, Medium, Semibold), page titles and empty-state headings only.
**Mono:** none by default; system monospace only for code or IDs if they need it.

**Character:** a warm humanist sans that stays out of the way. One family carries labels, buttons, tables and data, as Operate mode recommends.

### Hierarchy
Fixed rem scale (no fluid type), ratio about 1.125 to 1.2.
- **Page title** (Display 600, 1.5rem, 1.33, -0.01em): one per page.
- **Section title** (Text 600, 1.125rem, 1.45): panels, dialogs.
- **Body** (Text 400, 0.875rem, 1.45): forms, descriptions; prose capped at 65-75ch.
- **Table cell** (Text 400, 0.8125rem, 1.5): rows, truncated with ellipsis and full text on hover/title.
- **Label** (Text 500, 0.75rem, 1.33): badges, field labels, table headers; sentence case.
- **Stat** (Text 600, 1.75rem, 1.2, tabular numerals): metric numbers (data uses the Text cut, never Display).

### Named Rules
**The Display Is For Titles Rule.** Display never sets labels, buttons, table text or numbers.
**The Tabular Rule.** Numerals in tables, stats and IDs use tabular figures (`font-variant-numeric: tabular-nums`); confirm the font ships a `tnum` feature, else fall back for digits only.

## Layout

App frame: collapsible icon sidebar, top bar (breadcrumb left, search, notifications, theme, avatar right), content padded 24px. 4px spacing grid, gaps 8, 12, 16, 24. Tight groups, generous separation between sections, more space above a heading than below. Table rows 40px, header 36px. Responsive behavior is structural: sidebar becomes a sheet under 768px, stat cards go 4 to 2 to 1 columns, and the table scrolls horizontally inside its frame keeping ID and Subject first.

## Elevation & Depth

Flat by default: depth comes from the tonal step between Canvas and Panel and from hairline Line borders. Shadows appear only on inputs and buttons (a 1px soft `shadow-xs`) and on overlays.

### Shadow Vocabulary
- **Control** (`0 1px 2px rgb(26 25 22 / 0.06)`): inputs, outline buttons.
- **Overlay** (`0 8px 24px -8px rgb(26 25 22 / 0.18)`): popovers, dialogs, toasts; offset with soft blur, never a zero-offset halo.

### Named Rules
**The Flat-At-Rest Rule.** Surfaces are flat at rest; elevation is only for things that float above the page.

## Shapes

Soft but not bubbly: badges 6px, controls 8px, panels and tables 12px, the stat-card outer ring 16px. 1px borders everywhere; no colored side stripes on cards or alerts. Avatars are circles. Icons are Phosphor `regular`, 16px in controls and tables, 14px in labels, 20px in nav; `fill` only for the active nav item and selected states; always `currentColor`.

## Components

### Buttons
- **Shape:** 8px radius, 36px high (28px small).
- **Primary:** Signal Yellow with Ink text, the one per screen ("New Ticket").
- **Outline / Ghost:** Canvas with Line border / transparent; hover fills Panel.
- **States:** hover, focus-visible, active (1px press), disabled (50%, no pointer), loading (spinner in place, width kept).

### Badges
6px radius, 12px Medium, soft tone pairs above, optional leading icon or dot (health badges carry a dot).

### Stat card
Reference structure kept: Panel ring (16px) holding an uppercase 12px muted label with icon, and a Canvas inner panel (12px) with the number and a trend line (arrow shows direction, green or red shows good or bad). Loading is a skeleton. See open point 1 about the nested form.

### Data table
Panel header with sort affordances (`aria-sort`), checkbox column, ID, Subject (truncated), Status, Priority (icon + label), Assignee (avatar or initials, "Unassigned" muted), Category, Channel (icon + label), Health badge. Row hover fills Panel; selected rows get a faint yellow tint. Skeleton rows while loading; empty state teaches ("New tickets from email and the portal show up here") with a primary action.

### Inputs / Fields
Label above, hint or error below (error in destructive, with the recovery), 36px, 8px radius, Line border, focus ring 2px Ink with 2px offset (dark mode: Ink-dark). Placeholder is Ink Muted at 4.5:1.

### Navigation
Sidebar: logo tile (Signal Yellow), icon plus label rows, active row on Panel with `fill` icon; collapses to icons with tooltips. Top bar: breadcrumb, icon buttons with `aria-label`. Avoid modals for tasks that fit inline or in a side sheet; dialogs are for confirmations and destructive actions.

### Browser surfaces
Themed from the palette so nothing ships as a browser default: `::selection` is Signal Yellow at 35% with Ink text, `caret-color` Ink, thin scrollbars (Line thumb on Panel track), focus rings as above, tabular numerals in data.

## Motion

Operate rules: motion conveys state, feedback and continuity; routine transitions are 150 to 250 ms; no page-load choreography, no count-up on numbers, no repeated scroll reveals. Easing is a confident exponential ease-out (GSAP `expo.out`, CSS `cubic-bezier(0.16, 1, 0.3, 1)`); exits are faster than enters; no bounce or elastic. Animate `transform`, `opacity` (and bounded `clip-path`/blur for overlays) only. Everything goes through `gsap.matchMedia()` with `prefers-reduced-motion` turning it off; hover effects are skipped on touch. Tokens and helpers live in one `src/lib/motion.ts`.

| Where | What | Time |
| --- | --- | --- |
| Hover, press, focus | CSS transitions, no GSAP | 120 ms |
| Menus, popovers, dialogs, toasts | fade + 6px offset, origin-aware | 180 ms in, 120 ms out |
| Sidebar collapse | width and label fade | 220 ms |
| Table sort / row insert / row remove | FLIP reorder so rows slide to place | 240 ms |
| **Authored moment: a ticket changes** | the updated or newly arrived row settles in with a brief yellow-tint highlight that fades out, so an agent sees what just changed in a busy queue | 700 ms |

### Icon hover motion
Subtle, driven by hover or focus of the whole control (not the icon alone), reversible, never looping. One `useIconMotion` helper picks the effect by role:

| Role | Effect |
| --- | --- |
| Nav item icon | scale 1.08 and 1px lift; weight shifts to `fill` when active |
| Icon button (search, bell, chat) | scale 1.08; bell swings once (about 8 degrees); theme icon turns 20 degrees |
| Leading icon in a button | nudges 2px along its meaning (plus quarter-turn, download drops 2px) |
| Sort chevron | 1px shift in the sort direction |
| Row action icons | opacity 0.6 to 1 only |

Limits: at most 12% scale and 10 degrees rotation, about 160 ms in and 120 ms out.

## Do's and Don'ts

### Do:
- **Do** keep yellow to one primary action per screen and quiet state accents.
- **Do** pair every status color with an icon or label.
- **Do** use tinted neutrals for all text, including secondary text.
- **Do** build all states for each control: default, hover, focus, active, disabled, loading, error.
- **Do** use skeleton rows for loading and teaching empty states.
- **Do** theme selection, caret, scrollbars and focus rings from the palette.
- **Do** run animations through `src/lib/motion.ts` and respect reduced motion.

### Don't:
- **Don't** use Display for labels, buttons, tables or numbers.
- **Don't** add gradients (including gradient text), glass blur as decoration, hard offset shadows, or colored side-borders on cards and alerts.
- **Don't** animate page loads, count numbers up, or stagger sections on scroll.
- **Don't** put white text on yellow.
- **Don't** use emoji or Unicode glyphs as icons, or mix icon weights on one surface.
- **Don't** reach for a modal when an inline or side-sheet flow works.
- **Don't** add sparklines or progress rings as filler.

## Open points for you

1. **Stat cards:** I kept the reference's nested form (ring + inner panel) because the brief wins, but impeccable calls nested cards and the big-number-small-label metric template defaults to avoid. Keep as in the reference, or switch to one flat bordered tile with the number and trend inline?
2. **Yellow:** #FFC800 is my read of the reference; send the brand hex if you have one.
3. **Health** (On Track, Warning, Breached): assumed SLA-driven. Confirm.
4. **Tabular numerals:** I haven't confirmed Anthropic Sans ships `tnum`; I'll check the font file when implementing.
