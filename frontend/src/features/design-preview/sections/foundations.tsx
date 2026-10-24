import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { SoftBadge } from "@/components/patterns/ticket-meta"
import { Plus } from "@/icons"
import { Section, Specimen } from "../section"

const NEUTRALS = [
  ["background", "page"],
  ["surface", "panel"],
  ["muted", "muted"],
  ["secondary", "secondary"],
  ["border", "line"],
  ["muted-foreground", "soft text"],
  ["foreground", "ink"],
] as const

const TYPE = [
  ["Page title", "font-display text-2xl font-semibold tracking-tight", "Tickets"],
  ["Section title", "text-lg font-semibold", "Recent activity"],
  ["Body", "text-sm", "Reading is open to every member; permissions only unlock writes."],
  ["Table cell", "text-[0.8125rem]", "SSO SAML configuration failing on IdP callback"],
  ["Label", "text-xs font-medium", "Assignee"],
  ["Stat", "text-3xl font-semibold tabular-nums", "1,284"],
] as const

export function Foundations() {
  return (
    <Section id="foundations" title="Foundations" intro="Signal Yellow is the only accent. Neutrals lean warm. Hue otherwise means status.">
      <div className="grid gap-10 lg:grid-cols-2">
        <Specimen title="Accent: Signal Yellow" note="One primary action per screen. Always dark ink on yellow.">
          <div className="space-y-3 rounded-lg border p-4">
            <div className="flex h-12 items-center justify-center rounded-md bg-primary text-sm font-medium text-primary-foreground">primary / primary-foreground</div>
            <div className="flex flex-wrap items-center gap-2">
              <Button size="sm" icon={<Plus weight="bold" />}>New Ticket</Button>
              <Badge variant="secondary">Label</Badge>
              <span className="rounded-md bg-accent px-2 py-0.5 text-xs text-accent-foreground">accent wash</span>
              <span className="text-sm">text <mark className="rounded-sm">selection</mark> uses it at 40%</span>
            </div>
          </div>
        </Specimen>
        <Specimen title="Neutrals" note="Tinted toward the accent hue">
          <div className="grid grid-cols-4 overflow-hidden rounded-md border sm:grid-cols-7">
            {NEUTRALS.map(([token, name]) => (
              <div key={token} className="flex h-20 flex-col justify-end p-1.5" style={{ background: `var(--${token})` }}>
                <span className={`text-caption leading-tight ${token === "foreground" || token === "muted-foreground" ? "text-background" : "text-foreground"}`}>{name}</span>
              </div>
            ))}
          </div>
        </Specimen>
      </div>

      <Specimen title="Status tones" note="Soft badges: tinted background, strong text of the same hue. The label always says it too.">
        <div className="flex flex-wrap items-center gap-2 rounded-lg border p-4">
          <SoftBadge tone="info">Info</SoftBadge>
          <SoftBadge tone="warning">Warning</SoftBadge>
          <SoftBadge tone="danger">Danger</SoftBadge>
          <SoftBadge tone="success">Success</SoftBadge>
          <SoftBadge tone="neutral">Neutral</SoftBadge>
        </div>
      </Specimen>

      <Specimen title="Type" note="Anthropic Sans Text for everything; Display only on page titles. Tabular numerals in data.">
        <dl className="divide-y rounded-lg border">
          {TYPE.map(([name, cls, sample]) => (
            <div key={name} className="grid items-baseline gap-2 px-4 py-3 sm:grid-cols-[8rem_1fr]">
              <dt className="text-xs text-muted-foreground">{name}</dt>
              <dd className={cls}>{sample}</dd>
            </div>
          ))}
        </dl>
      </Specimen>

      <Specimen title="Radius and elevation" note="Badge 6, control 8, panel 12, stat ring 16. Shadows only on floating layers.">
        <div className="flex flex-wrap items-end gap-4">
          {["rounded-md", "rounded-lg", "rounded-xl", "rounded-2xl"].map((r) => (
            <div key={r} className={`flex h-14 w-24 items-center justify-center border bg-surface text-xs text-muted-foreground ${r}`}>{r.replace("rounded-", "")}</div>
          ))}
          <div className="flex h-14 w-32 items-center justify-center rounded-lg bg-popover text-xs text-muted-foreground shadow-pop">popover</div>
        </div>
      </Specimen>
    </Section>
  )
}
