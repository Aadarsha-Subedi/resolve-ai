import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { OptionLabel } from "@/components/patterns/option-select"
import type { SelectOption } from "@/components/patterns/ticket-meta"
import { Funnel } from "@/icons"
import { cn } from "@/lib/utils"

const ALL = "__all"

/** Filter dropdown. Unset it shows the filter's name; set it shows only the chosen option (no "Filter: Option" prefix). The first choice clears it. */
export function FilterSelect({ label, value, onChange, options, allLabel = "All", className }: { label: string; value?: string; onChange: (value: string | undefined) => void; options: SelectOption[]; allLabel?: string; className?: string }) {
  const items: SelectOption[] = [{ value: ALL, label: allLabel, icon: Funnel }, ...options]
  return (
    <Select value={value ?? ALL} onValueChange={(v) => onChange(v === ALL || v == null ? undefined : v)} items={items}>
      <SelectTrigger aria-label={label} className={cn("w-auto max-w-56 min-w-32", value && "border-primary", className)}>
        <SelectValue>
          {(v: string | null) => {
            const o = options.find((x) => x.value === v)
            return o ? <OptionLabel option={o} /> : <span className="flex items-center gap-2 text-muted-foreground"><Funnel className="size-4" aria-hidden />{label}</span>
          }}
        </SelectValue>
      </SelectTrigger>
      <SelectContent className="w-max max-w-[min(24rem,90vw)] min-w-(--anchor-width)">
        {items.map((o) => (
          <SelectItem key={o.value} value={o.value}><OptionLabel option={o} /></SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
