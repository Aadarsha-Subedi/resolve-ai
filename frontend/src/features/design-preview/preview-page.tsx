import { useEffect, useRef, useState } from "react"
import { Logo } from "@/components/patterns/logo"
import { ThemeToggle } from "@/components/patterns/theme-toggle"
import { Button } from "@/components/ui/button"
import { useReveal } from "@/motion"
import { useIconMotion } from "@/motion/icon-motion"
import { Actions } from "./sections/actions"
import { DataSection } from "./sections/data"
import { Feedback } from "./sections/feedback"
import { Forms } from "./sections/forms"
import { Foundations } from "./sections/foundations"
import { Menus } from "./sections/menus"
import { MotionSection } from "./sections/motion"
import { Navigation } from "./sections/navigation"

const TOC = [
  ["foundations", "Foundations"],
  ["actions", "Buttons"],
  ["forms", "Forms and filters"],
  ["data", "Tickets and metrics"],
  ["navigation", "Navigation and frame"],
  ["menus", "Menus and overlays"],
  ["feedback", "Feedback and states"],
  ["motion", "Motion"],
] as const

function useActiveSection() {
  const [active, setActive] = useState<string>(TOC[0][0])
  useEffect(() => {
    const on = () => {
      if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4) return setActive(TOC[TOC.length - 1][0])
      let cur: string = TOC[0][0]
      for (const [id] of TOC) {
        const el = document.getElementById(id)
        if (el && el.getBoundingClientRect().top <= 140) cur = id
      }
      setActive(cur)
    }
    on()
    window.addEventListener("scroll", on, { passive: true })
    return () => window.removeEventListener("scroll", on)
  }, [])
  return [active, setActive] as const
}

/** Living catalogue of the reusable components. Sample data is fake. */
export function DesignPreview() {
  const main = useRef<HTMLElement>(null)
  const root = useRef<HTMLDivElement>(null)
  const [active, setActive] = useActiveSection()
  useReveal(main)
  useIconMotion(root)
  return (
    <div ref={root} className="min-h-screen">
      <a href="#main" className="sr-only z-50 rounded bg-background px-3 py-2 text-sm focus:not-sr-only focus:fixed focus:top-2 focus:left-2">Skip to content</a>
      <header className="sticky top-0 z-30 flex h-14 items-center gap-4 border-b bg-background px-4">
        <Logo />
        <span aria-hidden className="hidden h-4 w-px bg-border sm:block" />
        <h1 className="hidden text-sm text-muted-foreground sm:block">Design preview</h1>
        <div className="ml-auto"><ThemeToggle /></div>
      </header>
      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-10 lg:grid-cols-[12rem_1fr]">
        <nav aria-label="Sections" className="sticky top-24 hidden h-fit lg:block">
          <ul className="space-y-0.5">
            {TOC.map(([id, label]) => (
              <li key={id}>
                <Button variant="ghost" size="sm" className={`w-full justify-start ${active === id ? "bg-muted text-foreground" : "text-muted-foreground"}`} nativeButton={false} render={<a href={`#${id}`} aria-current={active === id ? "location" : undefined} />}>{label}</Button>
              </li>
            ))}
          </ul>
        </nav>
        <main id="main" ref={main} className="min-w-0">
          <label className="mb-8 block lg:hidden">
            <span className="sr-only">Jump to section</span>
            <select value={active} onChange={(e) => { setActive(e.target.value); document.getElementById(e.target.value)?.scrollIntoView() }} className="h-(--ctl-h) w-full rounded-md border border-input bg-background px-2.5 text-sm">
              {TOC.map(([id, label]) => <option key={id} value={id}>{label}</option>)}
            </select>
          </label>
          <Foundations />
          <Actions />
          <Forms />
          <DataSection />
          <Navigation />
          <Menus />
          <Feedback />
          <MotionSection />
        </main>
      </div>
    </div>
  )
}
