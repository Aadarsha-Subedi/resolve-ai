import { useState, type ComponentType, type ReactNode } from "react"
import { DateRangePicker, type IsoRange } from "@/components/patterns/date-picker"
import { SearchBox } from "@/components/patterns/search-box"
import type { SelectOption } from "@/components/patterns/ticket-meta"
import { Button } from "@/components/ui/button"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuRadioGroup, DropdownMenuRadioItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { CalendarBlank, Funnel, FunnelX, X } from "@/icons"
import type { IconProps } from "@/icons"
import { parseIsoDate } from "@/lib/date"
import { cn } from "@/lib/utils"

type Base = { id: string; label: string; icon?: ComponentType<IconProps> }

/** One filter a table offers. The page owns the values (they live in the URL); the bar only draws them. */
export type FilterDef =
  | (Base & { kind: "select"; options: SelectOption[]; value?: string; onChange: (value: string | undefined) => void })
  | (Base & { kind: "date-range"; value: IsoRange; onChange: (value: IsoRange) => void })
  | (Base & { kind: "boolean"; value?: boolean; onChange: (value: boolean | undefined) => void })

export type FilterBarProps = {
  search?: { value: string; onCommit: (q: string | undefined) => void; placeholder: string }
  filters: FilterDef[]
  /** Clears every chip and the search text. */
  onClearAll: () => void
  /** Extra controls at the end of the row (for example "Manage categories"). */
  trailing?: ReactNode
  className?: string
}

const chipBase = "inline-flex h-7 items-center text-xs outline-none transition-colors focus-visible:ring-3 focus-visible:ring-ring/50"

const shortDate = (iso?: string) => {
  const date = parseIsoDate(iso)
  if (!date) return ""
  const sameYear = date.getFullYear() === new Date().getFullYear()
  return date.toLocaleDateString(undefined, { day: "numeric", month: "short", ...(sameYear ? {} : { year: "numeric" }) })
}

/** "1 Oct - 20 Oct" (the year only when it is not this year). */
export const compactRange = ({ from, to }: IsoRange): string => [shortDate(from), shortDate(to)].filter(Boolean).join(" - ")

const isActive = (f: FilterDef) => (f.kind === "select" ? f.value !== undefined : f.kind === "boolean" ? f.value === true : Boolean(f.value.from || f.value.to))
const clear = (f: FilterDef) => (f.kind === "select" ? f.onChange(undefined) : f.kind === "boolean" ? f.onChange(undefined) : f.onChange({}))

/** The chip's visible value, for example "Open" or "1 Oct - 20 Oct"; booleans have none (the name says it all). */
function valueText(f: FilterDef): string {
  if (f.kind === "select") return f.options.find((o) => o.value === f.value)?.label ?? f.value ?? ""
  if (f.kind === "date-range") return compactRange(f.value)
  return ""
}

function RemoveButton({ filter, onRemove }: { filter: FilterDef; onRemove: () => void }) {
  return (
    <button type="button" aria-label={`Remove ${filter.label} filter`} onClick={onRemove} className={cn(chipBase, "w-6 justify-center rounded-r-lg text-muted-foreground hover:bg-foreground/10 hover:text-foreground pointer-coarse:w-9")}>
      <X className="size-3" weight="bold" aria-hidden />
    </button>
  )
}

function ChipFrame({ children }: { children: ReactNode }) {
  return <span className="inline-flex items-center rounded-lg bg-muted text-foreground">{children}</span>
}

function ChipLabel({ filter, withValue = true }: { filter: FilterDef; withValue?: boolean }) {
  const Icon = filter.icon ?? Funnel
  const value = withValue ? valueText(filter) : ""
  return (
    <>
      <Icon className="size-3.5 text-muted-foreground" aria-hidden />
      <span className="text-muted-foreground">{filter.label}{value ? ":" : ""}</span>
      {value && <span className="font-medium">{value}</span>}
    </>
  )
}

function SelectChip({ filter, pending, onDone }: { filter: Extract<FilterDef, { kind: "select" }>; pending: boolean; onDone: () => void }) {
  const [open, setOpen] = useState(pending)
  return (
    <ChipFrame>
      <DropdownMenu open={open} onOpenChange={(next) => { setOpen(next); if (!next) onDone() }}>
        <DropdownMenuTrigger render={<button type="button" aria-label={`${filter.label}${filter.value ? `: ${valueText(filter)}` : ""}. Change`} className={cn(chipBase, "gap-1.5 rounded-l-lg pr-1.5 pl-2 hover:bg-foreground/10")} />}>
          <ChipLabel filter={filter} />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-max min-w-40">
          <DropdownMenuRadioGroup value={filter.value ?? ""} onValueChange={(v) => { filter.onChange(v || undefined); setOpen(false); onDone() }}>
            {filter.options.map((o) => (
              <DropdownMenuRadioItem key={o.value} value={o.value}>
                {o.icon && <o.icon className="size-4 text-muted-foreground" aria-hidden />}
                {o.label}
              </DropdownMenuRadioItem>
            ))}
          </DropdownMenuRadioGroup>
        </DropdownMenuContent>
      </DropdownMenu>
      {filter.value !== undefined && <RemoveButton filter={filter} onRemove={() => clear(filter)} />}
      {filter.value === undefined && <span className="w-1.5" />}
    </ChipFrame>
  )
}

function DateChip({ filter, pending, onDone }: { filter: Extract<FilterDef, { kind: "date-range" }>; pending: boolean; onDone: () => void }) {
  const active = isActive(filter)
  return (
    <ChipFrame>
      <DateRangePicker
        label={filter.label}
        value={filter.value}
        onChange={(range) => { filter.onChange(range); onDone() }}
        presets
        defaultOpen={pending}
        onOpenChange={(open) => { if (!open) onDone() }}
        trigger={<button type="button" aria-label={`${filter.label}${active ? `: ${compactRange(filter.value)}` : ""}. Change`} className={cn(chipBase, "gap-1.5 rounded-l-lg pr-1.5 pl-2 hover:bg-foreground/10")} />}
      />
      {active ? <RemoveButton filter={filter} onRemove={() => clear(filter)} /> : <span className="w-1.5" />}
    </ChipFrame>
  )
}

function BooleanChip({ filter }: { filter: Extract<FilterDef, { kind: "boolean" }> }) {
  return (
    <ChipFrame>
      <span className={cn(chipBase, "gap-1.5 pr-1.5 pl-2")}>
        <ChipLabel filter={filter} withValue={false} />
      </span>
      <RemoveButton filter={filter} onRemove={() => clear(filter)} />
    </ChipFrame>
  )
}

/**
 * The one filter row every table uses: a search box, a single Filter button that lists the filters not yet applied,
 * and a removable chip per applied filter ("Status: Open", "Created: 1 Oct - 20 Oct", "Waiting for reply").
 * Choosing a filter adds its chip and opens its value picker; a chip left without a value disappears again.
 * Date ranges open the range picker with 7 and 30 day presets. "Clear all" shows while any chip or search text is on.
 * Values stay with the caller (the URL), so the bar holds only which chip is waiting for its value.
 */
export function FilterBar({ search, filters, onClearAll, trailing, className }: FilterBarProps) {
  const [pendingId, setPendingId] = useState<string | null>(null)
  const shown = filters.filter((f) => isActive(f) || f.id === pendingId)
  const available = filters.filter((f) => !isActive(f) && f.id !== pendingId)
  const anyOn = filters.some(isActive) || Boolean(search?.value)

  const add = (f: FilterDef) => {
    if (f.kind === "boolean") return f.onChange(true)
    setPendingId(f.id)
  }
  const settle = () => setPendingId(null)

  return (
    <div role="search" className={cn("flex flex-wrap items-center gap-2", className)}>
      {search && <SearchBox value={search.value} onCommit={search.onCommit} placeholder={search.placeholder} />}
      <DropdownMenu>
        <DropdownMenuTrigger render={<Button variant="outline" icon={<Funnel />} disabled={available.length === 0} aria-label="Add filter" />}>Filter</DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-max min-w-44">
          {available.map((f) => {
            const Icon = f.icon ?? (f.kind === "date-range" ? CalendarBlank : Funnel)
            return <DropdownMenuItem key={f.id} onClick={() => add(f)}><Icon />{f.label}</DropdownMenuItem>
          })}
        </DropdownMenuContent>
      </DropdownMenu>
      {shown.map((f) =>
        f.kind === "select" ? <SelectChip key={f.id} filter={f} pending={f.id === pendingId} onDone={settle} />
        : f.kind === "date-range" ? <DateChip key={f.id} filter={f} pending={f.id === pendingId} onDone={settle} />
        : <BooleanChip key={f.id} filter={f} />,
      )}
      {anyOn && <Button variant="ghost" size="sm" icon={<FunnelX />} onClick={() => { settle(); onClearAll() }}>Clear all</Button>}
      {trailing}
    </div>
  )
}
