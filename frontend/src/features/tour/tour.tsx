import { useRouterState } from '@tanstack/react-router'
import { createContext, useCallback, useContext, useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

import { Button } from '@/components/ui/button'
import { TOUR_STEPS, tourPageFor, type TourPage } from '@/features/tour/steps'

const SEEN_KEY = 'resolveai-tour-seen'
const CARD_WIDTH = 320
const GAP = 12

function readSeen(): TourPage[] {
  try {
    return JSON.parse(localStorage.getItem(SEEN_KEY) ?? '[]') as TourPage[]
  } catch {
    return []
  }
}

function markSeen(page: TourPage) {
  try {
    const seen = readSeen()
    if (!seen.includes(page)) localStorage.setItem(SEEN_KEY, JSON.stringify([...seen, page]))
  } catch {
    /* storage unavailable: the tour just shows again next visit */
  }
}

type TourApi = { page: TourPage | null; replay: () => void }
const TourContext = createContext<TourApi>({ page: null, replay: () => {} })
export const useTour = () => useContext(TourContext)

/**
 * Guided tour for the page in view. It starts by itself the first time a page is opened while `autoStart` is
 * true (the demo workspace), and any time through `replay()` from the Help menu. Progress is kept per page in
 * localStorage, so a finished or skipped page stays quiet.
 */
export function TourProvider({ autoStart, children }: { autoStart: boolean; children: ReactNode }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname })
  const page = tourPageFor(pathname)
  const [active, setActive] = useState<{ page: TourPage; index: number } | null>(null)

  // A first visit to a page starts its tour; a tour for another page than the one in view is never shown.
  useEffect(() => {
    if (!autoStart || !page || readSeen().includes(page)) return
    const timer = window.setTimeout(() => setActive({ page, index: 0 }), 600)
    return () => window.clearTimeout(timer)
  }, [page, autoStart])

  const close = useCallback(() => {
    setActive((current) => {
      if (current) markSeen(current.page)
      return null
    })
  }, [])
  const replay = useCallback(() => {
    if (page) setActive({ page, index: 0 })
  }, [page])
  const value = useMemo(() => ({ page, replay }), [page, replay])

  return (
    <TourContext.Provider value={value}>
      {children}
      {active && active.page === page && <TourCard page={active.page} index={active.index} onIndex={(index) => setActive({ page: active.page, index })} onClose={close} />}
    </TourContext.Provider>
  )
}

type Box = { top: number; left: number; width: number; height: number }

function TourCard({ page, index, onIndex, onClose }: { page: TourPage; index: number; onIndex: (index: number) => void; onClose: () => void }) {
  const steps = TOUR_STEPS[page]
  const step = steps[index]
  const last = index === steps.length - 1
  const [box, setBox] = useState<Box | null>(null)
  const card = useRef<HTMLDivElement>(null)

  useLayoutEffect(() => {
    const measure = () => {
      const el = step.target ? document.querySelector(step.target) : null
      if (!el) return setBox(null)
      el.scrollIntoView({ block: 'nearest', behavior: 'instant' as ScrollBehavior })
      const r = el.getBoundingClientRect()
      setBox(r.width && r.height ? { top: r.top, left: r.left, width: r.width, height: r.height } : null)
    }
    measure()
    window.addEventListener('resize', measure)
    window.addEventListener('scroll', measure, true)
    return () => {
      window.removeEventListener('resize', measure)
      window.removeEventListener('scroll', measure, true)
    }
  }, [step])

  useEffect(() => card.current?.focus(), [index])
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const width = Math.min(CARD_WIDTH, window.innerWidth - 24)
  let style: React.CSSProperties
  if (box) {
    const below = box.top + box.height + GAP + 180 < window.innerHeight
    style = {
      width,
      left: Math.min(Math.max(12, box.left), window.innerWidth - width - 12),
      top: below ? box.top + box.height + GAP : undefined,
      bottom: below ? undefined : window.innerHeight - box.top + GAP,
    }
  } else {
    style = { width, left: (window.innerWidth - width) / 2, top: '35%' }
  }

  return createPortal(
    <div className="fixed inset-0 z-[60]">
      {/* The click-catcher keeps the page inert while the tour runs; the spotlight is a ring with a huge shadow dimming the rest. */}
      <div className="absolute inset-0" onClick={onClose} aria-hidden />
      {box ? (
        <div aria-hidden className="pointer-events-none absolute rounded-md ring-2 ring-primary shadow-[0_0_0_9999px_rgb(0_0_0/0.45)] transition-all duration-200 motion-reduce:transition-none" style={{ top: box.top - 4, left: box.left - 4, width: box.width + 8, height: box.height + 8 }} />
      ) : (
        <div aria-hidden className="pointer-events-none absolute inset-0 bg-black/45" />
      )}
      <div ref={card} role="dialog" aria-modal="true" aria-label={`Page tour, step ${index + 1} of ${steps.length}`} tabIndex={-1} style={style} className="absolute rounded-lg border bg-popover p-4 text-popover-foreground shadow-lg outline-none">
        <p className="text-xs text-muted-foreground tabular-nums">{index + 1} of {steps.length}</p>
        <h2 className="mt-1 font-display text-base font-semibold">{step.title}</h2>
        <p className="mt-1 text-sm text-muted-foreground text-pretty">{step.body}</p>
        <div className="mt-4 flex items-center justify-between gap-2">
          <Button variant="ghost" size="sm" onClick={onClose}>Skip</Button>
          <div className="flex gap-2">
            {index > 0 && <Button variant="outline" size="sm" onClick={() => onIndex(index - 1)}>Back</Button>}
            <Button size="sm" onClick={() => (last ? onClose() : onIndex(index + 1))}>{last ? 'Done' : 'Next'}</Button>
          </div>
        </div>
      </div>
    </div>,
    document.body,
  )
}
