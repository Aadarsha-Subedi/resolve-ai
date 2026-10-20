import type { ReactNode } from "react"
import { ArrowDownRight, ArrowUpRight } from "@/icons"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

export type StatTrend = {
  /** Signed change against the comparison period, e.g. 3 or -2. */
  change: number
  /** Relative change as text, e.g. "17.6%". */
  percent: string
  /** Whether the movement is good news. The arrow shows direction, the color shows meaning. */
  good: boolean
  /** Comparison label; defaults to "vs last week". */
  label?: string
}

/** Flat metric tile: label with icon, the number, its trend. One surface, no card inside a card. */
export function StatCard({ label, value, icon, trend, loading, className }: { label: string; value: ReactNode; icon?: ReactNode; trend?: StatTrend; loading?: boolean; className?: string }) {
  const Arrow = (trend?.change ?? 0) >= 0 ? ArrowUpRight : ArrowDownRight
  return (
    <div className={cn("rounded-xl border bg-card p-4", className)}>
      <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground [&_svg]:size-4">
        {icon}
        {label}
      </div>
      {loading ? <Skeleton className="mt-3 h-9 w-16" /> : <div className="mt-2 text-3xl font-semibold tabular-nums">{value}</div>}
      {trend && !loading && (
        <p className={cn("mt-1 flex items-center gap-1 text-xs tabular-nums", trend.good ? "text-success-text" : "text-danger-text")}>
          <Arrow weight="bold" className="size-3.5" aria-hidden />
          {Math.abs(trend.change)} ({trend.percent}) {trend.label ?? "vs last week"}
        </p>
      )}
    </div>
  )
}
