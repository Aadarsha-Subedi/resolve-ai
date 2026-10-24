import { CheckCircle, WarningCircle } from "@/icons"
import { cn } from "@/lib/utils"

/** Storage used against a limit. The words carry the state; the bar only repeats it. Warns from 80%. */
export function UsageMeter({ label, used, limit, format }: { label: string; used: number; limit: number; format: (n: number) => string }) {
  const share = limit > 0 ? Math.min(1, used / limit) : 0
  const pct = Math.round(share * 100)
  const warn = share >= 0.8
  const Icon = warn ? WarningCircle : CheckCircle
  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between gap-3 text-sm">
        <span className="font-medium">{label}</span>
        <span className="tabular-nums text-muted-foreground">{format(used)} of {format(limit)} · {pct}%</span>
      </div>
      <div role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct} className="h-1.5 overflow-hidden rounded-full bg-muted">
        <div className={cn("h-full rounded-full", warn ? "bg-warning" : "bg-primary")} style={{ width: `${pct}%` }} />
      </div>
      <p className={cn("flex items-center gap-1.5 text-xs", warn ? "text-warning-text" : "text-muted-foreground")}>
        <Icon weight="fill" className={cn("size-3.5", warn ? "text-warning" : "text-success")} aria-hidden />
        {share >= 1 ? "Full. Delete files to upload more." : warn ? "Almost full." : "Plenty of room."}
      </p>
    </div>
  )
}
