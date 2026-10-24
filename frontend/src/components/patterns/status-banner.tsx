import type { ReactNode } from "react"
import { Info, WarningCircle, XCircle } from "@/icons"
import { cn } from "@/lib/utils"

const TONES = {
  info: { icon: Info, color: "text-info" },
  warning: { icon: WarningCircle, color: "text-warning" },
  danger: { icon: XCircle, color: "text-destructive" },
} as const

/** Page-level state (archived, scheduled for deletion). Flat: an icon, one sentence, one action, a hairline below. */
export function StatusBanner({ tone = "info", title, children, action, className }: { tone?: keyof typeof TONES; title: string; children?: ReactNode; action?: ReactNode; className?: string }) {
  const { icon: Icon, color } = TONES[tone]
  return (
    <div role="status" className={cn("flex flex-wrap items-center gap-x-3 gap-y-2 border-b pb-3", className)}>
      <Icon weight="fill" className={cn("size-5 shrink-0", color)} aria-hidden />
      <p className="min-w-0 flex-1 text-sm"><span className="font-medium">{title}</span>{children && <span className="text-muted-foreground"> {children}</span>}</p>
      {action}
    </div>
  )
}
