import { useId, useState } from "react"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { ChartBar, Table } from "@/icons"
import { cn } from "@/lib/utils"

export type VolumeBucket = { start: string; end: string; created: number; resolved: number }

const W = 640
const H = 200
const PAD = { top: 8, right: 8, bottom: 22, left: 30 }

function niceMax(value: number): number {
  if (value <= 4) return 4
  const pow = 10 ** Math.floor(Math.log10(value))
  return Math.ceil(value / pow) * pow
}

const label = (iso: string) => new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { day: "numeric", month: "short" })

/**
 * Created and resolved per day or week as paired bars. Two series, fixed colours (chart-1 created, chart-2 resolved),
 * a legend always present, thin rounded marks, hairline grid, a tooltip on hover or keyboard focus, and a table view (newest bucket first, while the chart reads oldest to newest)
 * so no value depends on colour or pointer alone.
 */
export function VolumeChart({ buckets, granularity, className }: { buckets: VolumeBucket[]; granularity: "day" | "week"; className?: string }) {
  const [active, setActive] = useState<number | null>(null)
  const [table, setTable] = useState(false)
  const id = useId()
  const max = niceMax(Math.max(0, ...buckets.flatMap((b) => [b.created, b.resolved])))
  const innerW = W - PAD.left - PAD.right
  const innerH = H - PAD.top - PAD.bottom
  const slot = innerW / Math.max(1, buckets.length)
  const barW = Math.max(2, Math.min(10, slot / 2 - 2))
  const y = (v: number) => PAD.top + innerH - (v / max) * innerH
  const ticks = [0, max / 2, max]
  const labelEvery = Math.ceil(buckets.length / 8)
  const current = active !== null ? buckets[active] : null
  const total = buckets.reduce((sum, b) => sum + b.created + b.resolved, 0)

  return (
    <div className={cn("flex h-full flex-col gap-3", className)}>
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
        <ul className="flex items-center gap-4" aria-label="Legend">
          <li className="flex items-center gap-1.5"><span aria-hidden className="size-2.5 rounded-sm bg-chart-1" />Created</li>
          <li className="flex items-center gap-1.5"><span aria-hidden className="size-2.5 rounded-sm bg-chart-2" />Resolved</li>
        </ul>
        <ToggleGroup size="sm" spacing={1} value={[table ? "table" : "chart"]} onValueChange={(v) => v[0] && setTable(v[0] === "table")} aria-label="View">
          {([["chart", "Show chart", ChartBar], ["table", "Show as table", Table]] as const).map(([value, text, Icon]) => (
            <Tooltip key={value}>
              <TooltipTrigger render={<ToggleGroupItem value={value} aria-label={text} className="w-7 px-0" />}><Icon /></TooltipTrigger>
              <TooltipContent>{text}</TooltipContent>
            </Tooltip>
          ))}
        </ToggleGroup>
      </div>
      {/* The wrapper keeps the chart's natural height and grows with the panel, so the table fills exactly the space the chart does. */}
      <div className="relative aspect-[640/200] grow">
      {table ? (
        <div className="absolute inset-0 overflow-auto rounded-lg border">
          <table className="w-full text-xs tabular-nums">
            <caption className="sr-only">Tickets created and resolved per {granularity}</caption>
            <thead className="sticky top-0 bg-surface text-muted-foreground"><tr><th className="p-2 text-left font-medium">{granularity === "day" ? "Day" : "Week of"}</th><th className="p-2 text-right font-medium">Created</th><th className="p-2 text-right font-medium">Resolved</th></tr></thead>
            <tbody>{[...buckets].reverse().map((b) => <tr key={b.start} className="border-t"><td className="p-2">{label(b.start)}</td><td className="p-2 text-right">{b.created}</td><td className="p-2 text-right">{b.resolved}</td></tr>)}</tbody>
          </table>
        </div>
      ) : (
        <div className="absolute inset-0">
          <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMin meet" role="group" aria-labelledby={`${id}-t`} className="size-full overflow-visible" onMouseLeave={() => setActive(null)}>
            <title id={`${id}-t`}>{`Tickets created and resolved per ${granularity}. ${total === 0 ? "No activity in this period." : ""}`}</title>
            {ticks.map((t) => (
              <g key={t}>
                <line x1={PAD.left} x2={W - PAD.right} y1={y(t)} y2={y(t)} className="stroke-border" strokeWidth={1} />
                <text x={PAD.left - 6} y={y(t) + 3} textAnchor="end" className="fill-muted-foreground text-[10px] tabular-nums">{Math.round(t)}</text>
              </g>
            ))}
            {buckets.map((b, i) => {
              const cx = PAD.left + slot * i + slot / 2
              const bar = (value: number, offset: number, cls: string) =>
                value > 0 ? <rect x={cx + offset} y={y(value)} width={barW} height={y(0) - y(value)} rx={Math.min(3, barW / 2)} className={cls} /> : null
              return (
                <g key={b.start}>
                  {active === i && <rect x={PAD.left + slot * i} y={PAD.top} width={slot} height={innerH} className="fill-muted" opacity={0.7} />}
                  {bar(b.created, -barW - 1, "fill-chart-1")}
                  {bar(b.resolved, 1, "fill-chart-2")}
                  {i % labelEvery === 0 && <text x={cx} y={H - 6} textAnchor="middle" className="fill-muted-foreground text-[10px]">{label(b.start)}</text>}
                  <rect
                    x={PAD.left + slot * i}
                    y={PAD.top}
                    width={slot}
                    height={innerH}
                    fill="transparent"
                    tabIndex={0}
                    role="img"
                    aria-label={`${label(b.start)}${b.end !== b.start ? ` to ${label(b.end)}` : ""}: ${b.created} created, ${b.resolved} resolved`}
                    className="outline-none focus-visible:stroke-ring"
                    onMouseEnter={() => setActive(i)}
                    onFocus={() => setActive(i)}
                    onBlur={() => setActive(null)}
                  />
                </g>
              )
            })}
          </svg>
          {current && (
            <div role="status" className="pointer-events-none absolute top-0 right-0 rounded-md border bg-popover px-2.5 py-1.5 text-xs shadow-sm" style={{ boxShadow: "var(--pop-shadow)" }}>
              <p className="font-medium">{label(current.start)}{current.end !== current.start ? ` – ${label(current.end)}` : ""}</p>
              <p className="tabular-nums text-muted-foreground">{current.created} created · {current.resolved} resolved</p>
            </div>
          )}
        </div>
      )}
      </div>
    </div>
  )
}
