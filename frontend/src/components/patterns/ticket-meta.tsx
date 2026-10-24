import type { ReactNode } from "react"
import { ArrowDown, ArrowUp, ChatCircle, ChatsCircle, CheckCircle, CircleDashed, CircleHalf, Clock, CreditCard, DotsThree, Envelope, Equals, Flame, Globe, Info, Lightbulb, LockSimple, PlayCircle, Pulse, SlackLogo, UserCircle, UserGear, Warning, WarningOctagon, Wrench } from "@/icons"
import type { IconProps } from "@/icons"
import { cn } from "@/lib/utils"
import type { ComponentType } from "react"

/* Domain vocabulary shown in the ticket list. The backend owns the real values; these mirror the reference UI. */

export type Tone = "neutral" | "info" | "success" | "warning" | "danger"
export type TicketStatus = "open" | "in_progress" | "pending" | "resolved" | "closed"
export type TicketPriority = "urgent" | "high" | "medium" | "low" | "none"
export type TicketHealth = "on_track" | "warning" | "breached"
export type TicketChannel = "email" | "chat" | "slack" | "portal" | "agent"
export type TicketCategory = "billing" | "technical" | "account" | "feature_request" | "general" | "other"

const TONE: Record<Tone, string> = {
  neutral: "bg-muted text-muted-foreground",
  info: "bg-info-soft text-info-text",
  success: "bg-success-soft text-success-text",
  warning: "bg-warning-soft text-warning-text",
  danger: "bg-danger-soft text-danger-text",
}

const TONE_ICON: Record<Tone, ComponentType<IconProps>> = {
  neutral: CircleDashed,
  info: Info,
  success: CheckCircle,
  warning: Warning,
  danger: WarningOctagon,
}

/** Soft badge: tinted background, strong text and a filled icon in the same hue. Pass `icon` to override the tone's default; `icon={null}` hides it. */
export function SoftBadge({ tone = "neutral", icon, children, className }: { tone?: Tone; icon?: ComponentType<IconProps> | null; children: ReactNode; className?: string }) {
  const Icon = icon === null ? null : (icon ?? TONE_ICON[tone])
  return (
    <span className={cn("inline-flex h-6 items-center gap-1 rounded-md pr-2 pl-1.5 text-xs font-medium whitespace-nowrap", TONE[tone], className)}>
      {Icon && <Icon weight="fill" className="size-3.5" aria-hidden />}
      {children}
    </span>
  )
}

const STATUS: Record<TicketStatus, { label: string; tone: Tone; Icon: ComponentType<IconProps> }> = {
  open: { label: "Open", tone: "info", Icon: CircleHalf },
  in_progress: { label: "In progress", tone: "info", Icon: PlayCircle },
  pending: { label: "Pending", tone: "warning", Icon: Clock },
  resolved: { label: "Resolved", tone: "success", Icon: CheckCircle },
  closed: { label: "Closed", tone: "neutral", Icon: LockSimple },
}

export function TicketStatusBadge({ status }: { status: TicketStatus }) {
  const { label, tone, Icon } = STATUS[status]
  return <SoftBadge tone={tone} icon={Icon}>{label}</SoftBadge>
}

const HEALTH: Record<TicketHealth, { label: string; tone: Tone; Icon: ComponentType<IconProps> }> = {
  on_track: { label: "On track", tone: "neutral", Icon: Pulse },
  warning: { label: "Warning", tone: "warning", Icon: Warning },
  breached: { label: "Breached", tone: "danger", Icon: WarningOctagon },
}

export function HealthBadge({ health }: { health: TicketHealth }) {
  const { label, tone, Icon } = HEALTH[health]
  return <SoftBadge tone={tone} icon={Icon}>{label}</SoftBadge>
}

const PRIORITY: Record<TicketPriority, { label: string; Icon: ComponentType<IconProps>; tone: string }> = {
  urgent: { label: "Urgent", Icon: Flame, tone: "text-destructive" },
  high: { label: "High", Icon: ArrowUp, tone: "text-warning" },
  medium: { label: "Medium", Icon: Equals, tone: "text-foreground" },
  low: { label: "Low", Icon: ArrowDown, tone: "text-muted-foreground" },
  none: { label: "None", Icon: CircleDashed, tone: "text-muted-foreground" },
}

/** Priority is icon plus text, so it never depends on color. */
export function PriorityLabel({ priority, className }: { priority: TicketPriority; className?: string }) {
  const { label, Icon, tone } = PRIORITY[priority]
  return (
    <span className={cn("inline-flex items-center gap-1.5", className)}>
      <Icon weight="bold" className={cn("size-4", tone)} aria-hidden />
      {label}
    </span>
  )
}

const CHANNEL: Record<TicketChannel, { label: string; Icon: ComponentType<IconProps> }> = {
  email: { label: "Email", Icon: Envelope },
  chat: { label: "Chat", Icon: ChatCircle },
  slack: { label: "Slack", Icon: SlackLogo },
  portal: { label: "Portal", Icon: Globe },
  agent: { label: "Agent", Icon: UserGear },
}

export function ChannelLabel({ channel, className }: { channel: TicketChannel; className?: string }) {
  const { label, Icon } = CHANNEL[channel]
  return (
    <span className={cn("inline-flex items-center gap-1.5", className)}>
      <Icon className="size-4 text-muted-foreground" aria-hidden />
      {label}
    </span>
  )
}

export type SelectOption = { value: string; label: string; icon?: ComponentType<IconProps> }

export const STATUS_OPTIONS: SelectOption[] = (Object.keys(STATUS) as TicketStatus[]).map((v) => ({ value: v, label: STATUS[v].label, icon: STATUS[v].Icon }))
export const PRIORITY_OPTIONS: SelectOption[] = (Object.keys(PRIORITY) as TicketPriority[]).map((v) => ({ value: v, label: PRIORITY[v].label, icon: PRIORITY[v].Icon }))
export const CHANNEL_OPTIONS: SelectOption[] = (Object.keys(CHANNEL) as TicketChannel[]).map((v) => ({ value: v, label: CHANNEL[v].label, icon: CHANNEL[v].Icon }))

const CATEGORY: Record<TicketCategory, { label: string; Icon: ComponentType<IconProps> }> = {
  billing: { label: "Billing", Icon: CreditCard },
  technical: { label: "Technical", Icon: Wrench },
  account: { label: "Account", Icon: UserCircle },
  feature_request: { label: "Feature request", Icon: Lightbulb },
  general: { label: "General", Icon: ChatsCircle },
  other: { label: "Other", Icon: DotsThree },
}

export function CategoryLabel({ category, className }: { category: TicketCategory; className?: string }) {
  const { label, Icon } = CATEGORY[category]
  return (
    <span className={cn("inline-flex items-center gap-1.5", className)}>
      <Icon className="size-4 text-muted-foreground" aria-hidden />
      {label}
    </span>
  )
}

export const CATEGORY_OPTIONS: SelectOption[] = (Object.keys(CATEGORY) as TicketCategory[]).map((v) => ({ value: v, label: CATEGORY[v].label, icon: CATEGORY[v].Icon }))
