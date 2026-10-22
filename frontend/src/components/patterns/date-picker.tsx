import { useState, type ReactElement } from "react"
import type { DateRange } from "react-day-picker"
import { Button } from "@/components/ui/button"
import { Calendar } from "@/components/ui/calendar"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { CalendarBlank, X } from "@/icons"
import { parseIsoDate, toIsoDate } from "@/lib/date"
import { cn } from "@/lib/utils"

const show = (date: Date) => date.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" })

/** One calendar date. `value` and `onChange` use "YYYY-MM-DD" strings (what the API expects); `onChange(undefined)` clears it. */
export function DatePicker({ value, onChange, label, min, max, placeholder = "Pick a date", className }: {
  value?: string
  onChange: (value: string | undefined) => void
  /** Accessible name; also the button text while empty when no placeholder is wanted. */
  label: string
  min?: string
  max?: string
  placeholder?: string
  className?: string
}) {
  const [open, setOpen] = useState(false)
  const selected = parseIsoDate(value)
  const lo = parseIsoDate(min)
  const hi = parseIsoDate(max)
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger render={<Button variant="outline" slide={false} aria-label={selected ? `${label}: ${show(selected)}` : label} className={cn("w-40 justify-start gap-2 font-normal", !selected && "text-muted-foreground", className)} />}>
        <CalendarBlank className="size-4 shrink-0" aria-hidden />
        <span className="truncate">{selected ? show(selected) : placeholder}</span>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-auto">
        <Calendar
          mode="single"
          selected={selected}
          defaultMonth={selected ?? hi ?? lo}
          disabled={[...(lo ? [{ before: lo }] : []), ...(hi ? [{ after: hi }] : [])]}
          onSelect={(date) => {
            onChange(date ? toIsoDate(date) : undefined)
            setOpen(false)
          }}
        />
        {selected && <Button variant="ghost" size="sm" slide={false} icon={<X />} onClick={() => { onChange(undefined); setOpen(false) }}>Clear</Button>}
      </PopoverContent>
    </Popover>
  )
}

export type IsoRange = { from?: string; to?: string }

const addDays = (date: Date, days: number) => new Date(date.getFullYear(), date.getMonth(), date.getDate() + days)

/** "Last 7 days" and "Last 30 days" end today and include it. */
const PRESETS = [
  { label: "Last 7 days", days: 7 },
  { label: "Last 30 days", days: 30 },
] as const

export const formatRange = (value: IsoRange): string => {
  const from = parseIsoDate(value.from)
  const to = parseIsoDate(value.to)
  return from && to ? `${show(from)} – ${show(to)}` : from ? `${show(from)} –` : to ? `– ${show(to)}` : ""
}

/**
 * A from–to range in one popover (two months side by side on wide screens). Calls `onChange` once both ends are chosen, or with an empty range on Clear.
 * `presets` adds "Last 7 days" and "Last 30 days" shortcuts above the calendar (the calendar is the custom range).
 * `trigger` replaces the default button (the filter chips use it); `defaultOpen` and `onOpenChange` let a caller open it on mount and react to closing.
 */
export function DateRangePicker({ value, onChange, label, placeholder = "Pick a date range", className, presets = false, trigger, defaultOpen = false, onOpenChange }: {
  value: IsoRange
  onChange: (value: IsoRange) => void
  label: string
  placeholder?: string
  className?: string
  presets?: boolean
  trigger?: ReactElement
  defaultOpen?: boolean
  onOpenChange?: (open: boolean) => void
}) {
  const [open, setOpen] = useState(defaultOpen)
  const [draft, setDraft] = useState<DateRange | undefined>(() => {
    const start = parseIsoDate(value.from)
    return start ? { from: start, to: parseIsoDate(value.to) } : undefined
  })
  const from = parseIsoDate(value.from)
  const to = parseIsoDate(value.to)
  const text = formatRange(value)
  const close = () => {
    setOpen(false)
    onOpenChange?.(false)
  }
  return (
    <Popover open={open} onOpenChange={(next) => { setOpen(next); onOpenChange?.(next); if (next) setDraft(from ? { from, to } : undefined) }}>
      <PopoverTrigger render={trigger ?? <Button variant="outline" slide={false} aria-label={text ? `${label}: ${text}` : label} className={cn("min-w-52 justify-start gap-2 font-normal", !text && "text-muted-foreground", className)} />}>
        {!trigger && (
          <>
            <CalendarBlank className="size-4 shrink-0" aria-hidden />
            <span className="truncate">{text || placeholder}</span>
          </>
        )}
      </PopoverTrigger>
      <PopoverContent align="start" className="w-auto">
        {presets && (
          <div className="flex flex-wrap gap-1.5" role="group" aria-label="Quick ranges">
            {PRESETS.map(({ label: name, days }) => (
              <Button
                key={days}
                variant="outline"
                size="sm"
                icon={<CalendarBlank />}
                onClick={() => {
                  const today = new Date()
                  onChange({ from: toIsoDate(addDays(today, -(days - 1))), to: toIsoDate(today) })
                  close()
                }}
              >
                {name}
              </Button>
            ))}
            <span className="self-center text-xs text-muted-foreground">or pick a custom range</span>
          </div>
        )}
        <Calendar
          mode="range"
          numberOfMonths={2}
          selected={draft}
          defaultMonth={from}
          onSelect={(range) => {
            setDraft(range)
            if (range?.from && range.to) {
              onChange({ from: toIsoDate(range.from), to: toIsoDate(range.to) })
              close()
            }
          }}
        />
        {(from || to) && <Button variant="ghost" size="sm" slide={false} icon={<X />} onClick={() => { onChange({}); close() }}>Clear</Button>}
      </PopoverContent>
    </Popover>
  )
}
