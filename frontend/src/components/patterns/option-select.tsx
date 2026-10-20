import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { SelectOption } from "@/components/patterns/ticket-meta"
import { cn } from "@/lib/utils"

/** Select whose options each carry an icon; the trigger repeats the chosen option's icon. */
export function OptionSelect({ id, value, onValueChange, options, placeholder, className, size }: { id?: string; value?: string; onValueChange?: (value: string) => void; options: SelectOption[]; placeholder?: string; className?: string; size?: "sm" | "default" }) {
  return (
    <Select value={value} onValueChange={(v) => v != null && onValueChange?.(v)} items={options}>
      <SelectTrigger id={id} size={size} className={cn("w-full", className)}>
        <SelectValue placeholder={placeholder}>
          {(v: string | null) => {
            const o = options.find((x) => x.value === v)
            return o ? <OptionLabel option={o} /> : <span className="text-muted-foreground">{placeholder}</span>
          }}
        </SelectValue>
      </SelectTrigger>
      <SelectContent>
        {options.map((o) => (
          <SelectItem key={o.value} value={o.value}><OptionLabel option={o} /></SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}

export function OptionLabel({ option }: { option: SelectOption }) {
  const Icon = option.icon
  return (
    <span className="flex items-center gap-2">
      {Icon && <Icon className="size-4 text-muted-foreground" aria-hidden />}
      {option.label}
    </span>
  )
}
