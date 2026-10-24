import { useEffect, type RefObject } from "react"
import { EASE, gsap, reducedMotion } from "@/motion"

/**
 * Subtle icon hover motion. Put `data-icon-motion="<effect>"` on the control (button or link) whose
 * first <svg> should move; hover or keyboard focus of the whole control drives it, so the icon never
 * moves on its own. Reversible, never loops, transform only. Off for reduced motion and touch.
 */
export type IconEffect = "lift" | "swing" | "turn" | "spin" | "nudge" | "drop"

const IN = 0.16
const OUT = 0.12

function enter(effect: IconEffect, svg: SVGElement) {
  gsap.set(svg, { transformOrigin: "50% 50%" })
  switch (effect) {
    case "lift": return gsap.to(svg, { scale: 1.08, y: -1, duration: IN, ease: EASE, overwrite: "auto" })
    case "turn": return gsap.to(svg, { rotate: 20, duration: IN, ease: EASE, overwrite: "auto" })
    case "spin": return gsap.to(svg, { rotate: 90, duration: IN * 1.4, ease: EASE, overwrite: "auto" })
    case "nudge": return gsap.to(svg, { x: 2, duration: IN, ease: EASE, overwrite: "auto" })
    case "drop": return gsap.to(svg, { y: 2, duration: IN, ease: EASE, overwrite: "auto" })
    case "swing":
      return gsap.timeline({ overwrite: "auto" })
        .to(svg, { rotate: 8, duration: 0.08, ease: "power1.out" })
        .to(svg, { rotate: -6, duration: 0.1, ease: "power1.inOut" })
        .to(svg, { rotate: 0, duration: 0.1, ease: "power1.out" })
  }
}

function leave(svg: SVGElement) {
  gsap.to(svg, { scale: 1, x: 0, y: 0, rotate: 0, duration: OUT, ease: "power2.out", overwrite: "auto" })
}

export function useIconMotion(scope: RefObject<HTMLElement | null>) {
  useEffect(() => {
    const root = scope.current
    if (!root || reducedMotion() || window.matchMedia("(hover: none)").matches) return
    const host = (t: EventTarget | null) => (t instanceof Element ? t.closest<HTMLElement>("[data-icon-motion]") : null)
    const svgOf = (h: HTMLElement) => h.querySelector<SVGElement>("svg")
    const on = (e: Event) => {
      const h = host(e.target)
      const svg = h && svgOf(h)
      if (!h || !svg || (e instanceof MouseEvent && h.contains(e.relatedTarget as Node))) return
      enter(h.dataset.iconMotion as IconEffect, svg)
    }
    const off = (e: Event) => {
      const h = host(e.target)
      const svg = h && svgOf(h)
      if (!h || !svg || (e instanceof MouseEvent && h.contains(e.relatedTarget as Node))) return
      leave(svg)
    }
    root.addEventListener("mouseover", on)
    root.addEventListener("mouseout", off)
    root.addEventListener("focusin", on)
    root.addEventListener("focusout", off)
    return () => {
      root.removeEventListener("mouseover", on)
      root.removeEventListener("mouseout", off)
      root.removeEventListener("focusin", on)
      root.removeEventListener("focusout", off)
    }
  }, [scope])
}
