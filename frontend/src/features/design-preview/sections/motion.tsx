import { useRef, useState } from "react"
import { Button } from "@/components/ui/button"
import { ArrowsClockwise, Bell, DownloadSimple, Gear, MagnifyingGlass, Plus, SidebarSimple, Sun } from "@/icons"
import type { IconEffect } from "@/motion/icon-motion"
import { useIconMotion } from "@/motion/icon-motion"
import { EASE, gsap, reducedMotion, useGSAP } from "@/motion"
import { Section, Specimen } from "../section"
import { cn } from "@/lib/utils"

const ICONS: [string, IconEffect, typeof Bell][] = [
  ["Nav item", "lift", Gear],
  ["Search", "lift", MagnifyingGlass],
  ["Notifications", "swing", Bell],
  ["Theme", "turn", Sun],
  ["Sidebar", "turn", SidebarSimple],
  ["New", "spin", Plus],
  ["Export", "drop", DownloadSimple],
]

const ROWS = ["Webhook delivery delays", "SSO callback failing", "Proration breakdown"]

export function MotionSection() {
  const icons = useRef<HTMLDivElement>(null)
  useIconMotion(icons)
  const stage = useRef<HTMLUListElement>(null)
  const [fresh, setFresh] = useState(-1)
  const { contextSafe } = useGSAP({ scope: stage })
  /** The authored moment: a changed row settles in with a brief yellow wash that fades, so an agent sees what just changed. */
  // eslint-disable-next-line react-hooks/refs -- contextSafe only reads the ref when invoked from the click handler
  const flash = contextSafe((i: number) => {
    setFresh(i)
    if (reducedMotion()) return
    const row = stage.current?.children[i]
    if (row) gsap.fromTo(row, { backgroundColor: "color-mix(in oklch, var(--primary) 35%, transparent)" }, { backgroundColor: "color-mix(in oklch, var(--primary) 0%, transparent)", duration: 0.7, ease: EASE })
  })
  return (
    <Section id="motion" title="Motion" intro="Motion explains state; it is not decoration. CSS handles hover and open states. GSAP handles icon hover, row changes and layout flips. Everything turns off under reduced motion and on touch.">
      <div className="grid gap-10 lg:grid-cols-2">
        <Specimen title="Icon hover" note="Hover or focus the control. At most 12% scale or 20° turn, about 160 ms in, 120 ms out, always reversible.">
          <div ref={icons} className="flex flex-wrap gap-2">
            {ICONS.map(([label, effect, Icon]) => (
              <Button key={label} variant="outline" icon={<Icon />} data-icon-motion={effect}>{label}</Button>
            ))}
          </div>
        </Specimen>
        <Specimen title="A ticket changes" note="Click a row to simulate an update. The row highlights and fades so the change is easy to find in a busy queue.">
          <ul ref={stage} className="divide-y rounded-lg border">
            {ROWS.map((r, i) => (
              <li key={r}>
                <button type="button" onClick={() => flash(i)} className={cn("flex w-full items-center justify-between px-4 py-2.5 text-left text-sm outline-none focus-visible:bg-muted", fresh === i && "font-medium")}>
                  {r}
                  <ArrowsClockwise className="size-4 text-muted-foreground" aria-hidden />
                </button>
              </li>
            ))}
          </ul>
        </Specimen>
      </div>
    </Section>
  )
}
