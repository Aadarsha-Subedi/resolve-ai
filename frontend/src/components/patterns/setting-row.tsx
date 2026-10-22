import type { ReactNode } from "react"
import { cn } from "@/lib/utils"

/**
 * One setting: title and description stacked on the left, the control on the right, hairline separators between rows
 * (put rows inside `SettingGroup`). On narrow screens the control drops below the text.
 */
export function SettingRow({ title, description, htmlFor, danger = false, children, className }: { title: ReactNode; description?: ReactNode; htmlFor?: string; danger?: boolean; children: ReactNode; className?: string }) {
  const Title = htmlFor ? "label" : "p"
  return (
    <div className={cn("flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between sm:gap-8", className)}>
      <div className="min-w-0 space-y-0.5 sm:max-w-md">
        <Title {...(htmlFor ? { htmlFor } : {})} className={cn("block text-sm font-medium", danger && "text-destructive")}>{title}</Title>
        {description && <div className="text-sm text-muted-foreground">{description}</div>}
      </div>
      <div className="flex min-w-0 flex-wrap items-center gap-2 sm:shrink-0 sm:justify-end">{children}</div>
    </div>
  )
}

/** A titled run of `SettingRow`s separated by hairlines. */
export function SettingGroup({ title, id, children }: { title: ReactNode; id: string; children: ReactNode }) {
  return (
    <section aria-labelledby={id}>
      <h2 id={id} className="pb-1 text-sm font-semibold">{title}</h2>
      <div className="divide-y border-y">{children}</div>
    </section>
  )
}
