import { DayPicker, type DayPickerProps } from "react-day-picker"
import { CaretLeft, CaretRight } from "@/icons"
import { buttonVariants } from "@/components/ui/button"
import { cn } from "@/lib/utils"

/**
 * Month grid on react-day-picker, themed with the design tokens. Arrow keys move between days, Page Up/Down
 * change month, Enter or Space selects. It does not animate, so reduced motion needs no special case.
 */
function Calendar({ className, classNames, showOutsideDays = true, ...props }: DayPickerProps) {
  return (
    <DayPicker
      showOutsideDays={showOutsideDays}
      className={cn("p-1", className)}
      classNames={{
        root: "w-fit",
        months: "relative flex flex-col gap-4 sm:flex-row",
        month: "flex flex-col gap-3",
        month_caption: "flex h-8 items-center justify-center",
        caption_label: "text-sm font-medium",
        nav: "absolute inset-x-0 top-0 flex items-center justify-between",
        button_previous: cn(buttonVariants({ variant: "ghost", size: "icon-sm" }), "size-8 p-0 aria-disabled:opacity-40"),
        button_next: cn(buttonVariants({ variant: "ghost", size: "icon-sm" }), "size-8 p-0 aria-disabled:opacity-40"),
        month_grid: "w-full border-collapse",
        weekdays: "flex",
        weekday: "w-8 text-center text-[0.75rem] font-medium text-muted-foreground",
        week: "mt-1 flex w-full",
        day: "relative size-8 p-0 text-center text-sm [&:has([aria-selected])]:rounded-md",
        day_button: "inline-flex size-8 items-center justify-center rounded-md text-sm tabular-nums outline-none transition-colors hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring/50 pointer-coarse:size-10",
        selected: "[&>button]:bg-primary [&>button]:text-primary-foreground [&>button]:hover:bg-primary",
        range_start: "rounded-l-md bg-accent",
        range_end: "rounded-r-md bg-accent",
        range_middle: "bg-accent [&>button]:bg-transparent [&>button]:text-accent-foreground [&>button]:rounded-none",
        today: "[&>button]:font-semibold [&>button]:ring-1 [&>button]:ring-border",
        outside: "text-muted-foreground opacity-60",
        disabled: "opacity-40 [&>button]:pointer-events-none",
        hidden: "invisible",
        ...classNames,
      }}
      components={{
        Chevron: ({ orientation, className: c }) => (orientation === "left" ? <CaretLeft className={cn("size-4", c)} /> : <CaretRight className={cn("size-4", c)} />),
      }}
      {...props}
    />
  )
}

export { Calendar }
