import { Fragment } from "react"
import { cn } from "@/lib/utils"

/** A key cap: hairline border, a heavier bottom edge and a faint top highlight so it reads as a physical key. */
function Kbd({ className, ...props }: React.ComponentProps<"kbd">) {
  return (
    <kbd
      data-slot="kbd"
      className={cn(
        "pointer-events-none inline-flex h-5 w-fit min-w-5 items-center justify-center gap-1 rounded-[5px] border border-b-2 border-border bg-background px-1.5 font-sans text-[0.6875rem] leading-none font-medium text-muted-foreground shadow-[inset_0_1px_0_oklch(1_0_0/0.6)] select-none dark:shadow-none in-data-[slot=tooltip-content]:border-background/25 in-data-[slot=tooltip-content]:bg-background/15 in-data-[slot=tooltip-content]:text-background [&_svg:not([class*='size-'])]:size-3",
        className
      )}
      {...props}
    />
  )
}

function KbdGroup({ className, ...props }: React.ComponentProps<"span">) {
  return <span data-slot="kbd-group" className={cn("inline-flex items-center gap-1", className)} {...props} />
}

/** A shortcut as key caps. "G T" is a sequence (press in turn), "Mod+K" a chord. "Mod" shows as ⌘ on Apple platforms and Ctrl elsewhere. */
const isApple = typeof navigator !== "undefined" && /Mac|iPhone|iPad/.test(navigator.platform)
const SYMBOL: Record<string, string> = { mod: isApple ? "⌘" : "Ctrl", shift: "⇧", alt: isApple ? "⌥" : "Alt", enter: "↵", esc: "Esc" }

function Shortcut({ keys, className, ...props }: { keys: string } & Omit<React.ComponentProps<"span">, "children">) {
  const sequence = keys.split(" ")
  return (
    <KbdGroup aria-label={keys} className={cn("gap-1.5", className)} {...props}>
      {sequence.map((step, i) => (
        <Fragment key={i}>
          {i > 0 && <span aria-hidden className="text-[0.6875rem] text-muted-foreground">then</span>}
          <KbdGroup>
            {step.split("+").map((k) => (
              <Kbd key={k}>{SYMBOL[k.toLowerCase()] ?? k}</Kbd>
            ))}
          </KbdGroup>
        </Fragment>
      ))}
    </KbdGroup>
  )
}

export { Kbd, KbdGroup, Shortcut }
