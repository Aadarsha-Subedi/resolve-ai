import { useGSAP } from "@gsap/react"
import gsap from "gsap"
import { Flip } from "gsap/Flip"
import { ScrollTrigger } from "gsap/ScrollTrigger"
import { useEffect, useRef, useState, type RefObject } from "react"

gsap.registerPlugin(useGSAP, Flip, ScrollTrigger)

export { gsap, Flip, useGSAP }

/** All orchestrated motion goes through here so reduced motion is honoured in one place. */
export const reducedMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches

export const EASE = "expo.out"

/** Fades and lifts every `[data-reveal]` inside scope, staggered, once it scrolls into view. */
export function useReveal(scope: RefObject<HTMLElement | null>, deps: unknown[] = []) {
  useGSAP(
    () => {
      if (reducedMotion()) return
      // Content stays visible by default; only items below the fold are hidden, once, until they scroll in.
      const items = gsap.utils.toArray<HTMLElement>("[data-reveal]", scope.current).filter((el) => el.getBoundingClientRect().top > window.innerHeight * 0.94)
      gsap.set(items, { opacity: 0, y: 12 })
      items.forEach((el) => {
        const show = () => gsap.to(el, { opacity: 1, y: 0, duration: 0.6, ease: EASE, overwrite: true })
        ScrollTrigger.create({
          trigger: el,
          start: "top 94%",
          end: "bottom top",
          // Fires for normal scroll and for anchor jumps that land inside or past the item.
          onToggle: (self) => self.isActive && show(),
          onLeave: show,
          once: false,
        })
      })
      requestAnimationFrame(() => ScrollTrigger.refresh())
    },
    { scope, dependencies: deps, revertOnUpdate: true },
  )
}

/** Count-up number; renders the final value immediately under reduced motion. */
export function CountUp({ value, className }: { value: number; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null)
  const [shown, setShown] = useState(reducedMotion() ? value : 0)
  useEffect(() => {
    if (reducedMotion()) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- reduced motion shows the final value immediately
      setShown(value)
      return
    }
    const o = { v: shown }
    const tween = gsap.to(o, { v: value, duration: 1.1, ease: EASE, onUpdate: () => setShown(Math.round(o.v)) })
    return () => {
      tween.kill()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value])
  return (
    <span ref={ref} className={className}>
      {shown.toLocaleString()}
    </span>
  )
}

/**
 * Animates layout changes of `[data-flip-id]` children. Call the returned `capture()`
 * right before changing the state that reorders them; `key` is that state.
 */
export function useFlip(scope: RefObject<HTMLElement | null>, key: unknown) {
  const state = useRef<Flip.FlipState | null>(null)
  useGSAP(
    () => {
      if (!state.current) return
      if (!reducedMotion()) Flip.from(state.current, { duration: 0.5, ease: EASE, stagger: 0.02 })
      state.current = null
    },
    { scope, dependencies: [key] },
  )
  return () => {
    if (scope.current) state.current = Flip.getState(scope.current.querySelectorAll("[data-flip-id]"))
  }
}
