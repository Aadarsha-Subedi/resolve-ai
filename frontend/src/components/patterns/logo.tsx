import { Command } from "@/icons"
import { cn } from "@/lib/utils"

/** ResolveAI mark: Phosphor Command in a Signal Yellow tile, with wordmark. */
export function Logo({ className, mark = false }: { className?: string; mark?: boolean }) {
  return (
    <span className={cn("inline-flex items-center gap-2 font-semibold tracking-tight whitespace-nowrap", className)}>
      <span className="grid size-6 shrink-0 place-items-center rounded-md bg-primary text-primary-foreground">
        <Command weight="bold" className="size-4" aria-hidden />
      </span>
      {!mark && <span>ResolveAI</span>}
    </span>
  )
}
