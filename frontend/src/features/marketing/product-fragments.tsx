import { ChannelLabel, HealthBadge, PriorityLabel, TicketStatusBadge } from "@/components/patterns/ticket-meta"
import { Assignee } from "@/components/patterns/assignee"
import { Button } from "@/components/ui/button"
import { Field, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { OptionSelect } from "@/components/patterns/option-select"
import { CreditCard, MagnifyingGlass, PaperPlaneTilt, UserCircle, Wrench } from "@/icons"
import { TICKETS } from "@/features/design-preview/data"
import { cn } from "@/lib/utils"

/** Browser-window frame for product fragments. Decorative: the real screens are the product, these are samples. */
export function Window({ title, children, className }: { title: string; children: React.ReactNode; className?: string }) {
  return (
    <div aria-hidden className={cn("overflow-hidden rounded-xl border bg-background shadow-[0_24px_48px_-24px_oklch(0_0_0/0.35)]", className)}>
      <div className="flex h-9 items-center gap-1.5 border-b bg-surface px-3">
        <span className="size-2.5 rounded-full bg-border" /><span className="size-2.5 rounded-full bg-border" /><span className="size-2.5 rounded-full bg-border" />
        <span className="ml-3 text-xs text-muted-foreground">{title}</span>
      </div>
      {children}
    </div>
  )
}

const INBOX = [TICKETS[6], TICKETS[7], TICKETS[2], TICKETS[3], TICKETS[5], TICKETS[8]]

/** The agent queue: ordered by what is late first. */
export function InboxFragment({ rowsRef }: { rowsRef?: React.Ref<HTMLUListElement> }) {
  return (
    <Window title="Tickets · Open and pending">
      <ul ref={rowsRef} className="divide-y text-[0.8125rem]">
        {INBOX.map((t) => (
          <li key={t.id} data-row className="grid grid-cols-[1fr_auto] items-center gap-3 px-4 py-2.5 sm:grid-cols-[3rem_1fr_auto_auto_auto]">
            <span className="hidden text-muted-foreground tabular-nums sm:block">#{String(t.number).padStart(3, "0")}</span>
            <span className="truncate font-medium">{t.subject}</span>
            <span className="hidden sm:block"><TicketStatusBadge status={t.status} /></span>
            <span className="hidden md:block"><PriorityLabel priority={t.priority} /></span>
            <HealthBadge health={t.health} />
          </li>
        ))}
      </ul>
    </Window>
  )
}

/** What one agent sees on a single late ticket. */
export function TicketFragment() {
  const t = TICKETS[6]
  return (
    <Window title={`Ticket #0${t.number}`}>
      <div className="space-y-4 p-5 text-sm">
        <div className="space-y-1">
          <p className="font-display text-lg font-semibold">{t.subject}</p>
          <div className="flex flex-wrap items-center gap-3 text-[0.8125rem]">
            <TicketStatusBadge status={t.status} /><PriorityLabel priority={t.priority} /><ChannelLabel channel={t.channel} /><HealthBadge health={t.health} />
          </div>
        </div>
        <div className="flex items-center gap-2 text-[0.8125rem] text-muted-foreground"><Assignee name="Jason Duong" /> replied 2 hours ago</div>
      </div>
    </Window>
  )
}

const CATEGORIES = [
  { value: "billing", label: "Billing", icon: CreditCard },
  { value: "technical", label: "Technical", icon: Wrench },
  { value: "account", label: "Account", icon: UserCircle },
]

/** The customer's side: a plain form in the workspace portal. */
export function PortalFragment() {
  return (
    <Window title="support.acme.com · New request">
      <div className="space-y-4 p-5">
        <Field><FieldLabel>What do you need help with?</FieldLabel><Input tabIndex={-1} defaultValue="Webhook deliveries are arriving late" /></Field>
        <Field><FieldLabel>Category</FieldLabel><OptionSelect value="technical" options={CATEGORIES} /></Field>
        <Field><FieldLabel>Details</FieldLabel><Textarea tabIndex={-1} defaultValue="Since Tuesday, events reach our endpoint 5 to 10 minutes after they are sent." className="min-h-20" /></Field>
        <Button tabIndex={-1} icon={<PaperPlaneTilt weight="fill" />}>Send to support</Button>
      </div>
    </Window>
  )
}

const ARTICLES = [
  ["Set up SSO with your identity provider", "Account"],
  ["Why webhook deliveries can be delayed", "Technical"],
  ["Read your invoice and proration", "Billing"],
  ["Invite teammates and set their role", "Account"],
]

/** Answers written once, found while replying. */
export function KnowledgeFragment() {
  return (
    <Window title="Knowledge base">
      <div className="p-4">
        <div className="flex h-9 items-center gap-2 rounded-lg border bg-input/30 px-3 text-sm text-muted-foreground"><MagnifyingGlass className="size-4" />webhook</div>
        <ul className="mt-2 divide-y text-sm">
          {ARTICLES.map(([title, tag]) => (
            <li key={title} className="flex h-11 items-center justify-between gap-3"><span className="truncate">{title}</span><span className="text-xs text-muted-foreground">{tag}</span></li>
          ))}
        </ul>
      </div>
    </Window>
  )
}
