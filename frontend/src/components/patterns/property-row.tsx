import type { ReactNode } from "react"
import { Lock } from "@/icons"
import { cn } from "@/lib/utils"

/** One labelled property of a record. When the viewer may not change it, `lockedBy` is the plain-language reason (see `useLockText`), written beside the value. */
export function PropertyRow({ label, htmlFor, lockedBy, children, className }: { label: string; htmlFor?: string; lockedBy?: string; children: ReactNode; className?: string }) {
  return (
    <div className={cn("grid gap-1 py-2 sm:grid-cols-[8rem_1fr] sm:items-center sm:gap-4", className)}>
      <label htmlFor={htmlFor} className="text-sm text-muted-foreground">{label}</label>
      <div className="min-w-0 space-y-1">
        <div className="min-w-0">{children}</div>
        {lockedBy && <p className="inline-flex items-center gap-1 text-xs text-muted-foreground"><Lock className="size-3.5" aria-hidden />{lockedBy}</p>}
      </div>
    </div>
  )
}
