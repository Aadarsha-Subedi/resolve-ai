import { useEffect, useRef, useState } from "react"
import { Button } from "@/components/ui/button"
import { CheckCircle, FilePdf, PaperPlaneTilt, Sparkle, Spinner } from "@/icons"
import { reducedMotion } from "@/motion"
import { cn } from "@/lib/utils"

const FILE = "refund-policy.pdf"
const QUESTION = "Hi, I was charged twice for my March invoice. How do I get a refund?"
const CONTEXT = "Duplicate charges are refunded in full to the original card within 5 business days of the request."
const DRAFT = "Hi Maya, sorry about the double charge. We have refunded the duplicate payment in full. It returns to your original card within 5 business days. Reply here if it has not arrived by then."

const BASE_ARTICLES = ["Set up SSO with your identity provider", "Invite teammates and set their role"]

type Scene = "knowledge" | "ticket"
type Phase = "idle" | "dragging" | "indexing" | "indexed" | "inbound" | "asking" | "context" | "drafting" | "sending" | "sent"
type Target = "rest" | "drop" | "ask" | "send"

/** Reduced motion starts on, and stays at, the finished state. */
const STATIC = typeof window !== "undefined" && reducedMotion()

const sleep = (ms: number) => new Promise<void>((resolve) => window.setTimeout(resolve, ms))

/**
 * The hero's product story, scripted: a PDF goes into the knowledge base, a customer reports a double charge,
 * the agent asks AI for context, AI drafts the reply from that file, the agent sends it. It loops.
 * Decorative and fake (sample names only); reduced motion shows the finished state and does not loop.
 */
export function HeroDemo() {
  const [scene, setScene] = useState<Scene>(STATIC ? "ticket" : "knowledge")
  const [phase, setPhase] = useState<Phase>(STATIC ? "sent" : "idle")
  const [typed, setTyped] = useState(STATIC ? DRAFT.length : 0)
  const [target, setTarget] = useState<Target>("rest")
  const [cursor, setCursor] = useState<{ x: number; y: number } | null>(null)
  const frame = useRef<HTMLDivElement>(null)

  /** Moves the pointer to the centre of the named control. Positions are measured, so any width works. */
  useEffect(() => {
    const box = frame.current
    const el = box?.querySelector<HTMLElement>(`[data-target="${target}"]`)
    if (!box || !el) return
    const place = () => {
      const a = box.getBoundingClientRect()
      const b = el.getBoundingClientRect()
      setCursor({ x: b.left - a.left + b.width / 2, y: b.top - a.top + b.height / 2 })
    }
    place()
    window.addEventListener("resize", place)
    return () => window.removeEventListener("resize", place)
  }, [target, scene])

  useEffect(() => {
    if (STATIC) return
    let live = true
    const step = async (ms: number) => {
      await sleep(ms)
      if (!live) throw new Error("stopped")
    }
    const run = async () => {
      while (live) {
        setScene("knowledge"); setPhase("idle"); setTyped(0); setTarget("rest")
        await step(900)
        setPhase("dragging"); setTarget("drop")
        await step(1100)
        setPhase("indexing")
        await step(1300)
        setPhase("indexed")
        await step(1400)
        setScene("ticket"); setPhase("inbound"); setTarget("rest")
        await step(1500)
        setTarget("ask")
        await step(900)
        setPhase("asking")
        await step(1100)
        setPhase("context")
        await step(1700)
        setPhase("drafting")
        for (let i = 1; i <= DRAFT.length; i += 3) {
          setTyped(i)
          await step(22)
        }
        setTyped(DRAFT.length)
        await step(500)
        setTarget("send")
        await step(800)
        setPhase("sending")
        await step(500)
        setPhase("sent")
        await step(3200)
      }
    }
    run().catch(() => {})
    return () => { live = false }
  }, [])

  return (
    <figure
      role="img"
      aria-label={`Product preview: a ${FILE} file is added to the knowledge base. A customer writes that they were charged twice. The agent asks AI, which finds the refund policy and drafts a reply, and the agent sends it.`}
      className="m-0"
    >
      <div ref={frame} className="relative overflow-hidden rounded-xl border bg-background shadow-[0_24px_48px_-24px_oklch(0_0_0/0.35)]" aria-hidden>
        <div className="flex h-9 items-center gap-1.5 border-b bg-surface px-3">
          <span className="size-2.5 rounded-full bg-border" /><span className="size-2.5 rounded-full bg-border" /><span className="size-2.5 rounded-full bg-border" />
          <span className="ml-3 text-xs text-muted-foreground">{scene === "knowledge" ? "Knowledge base" : "Ticket #118 · Billing"}</span>
        </div>

        <div className="h-[25rem] text-sm sm:h-[26rem]">
          {scene === "knowledge" ? (
            <div className="space-y-3 p-4 sm:p-5">
              <div
                data-target="drop"
                className={cn("flex h-24 flex-col items-center justify-center gap-1 rounded-lg border-2 border-dashed text-muted-foreground transition-colors duration-300", phase === "dragging" && "border-primary bg-primary/10 text-foreground")}
              >
                <span>Drop files to add them to the knowledge base</span>
                <span className="text-xs">PDF, Word or Markdown</span>
              </div>
              <ul className="divide-y rounded-lg border">
                {(phase === "indexing" || phase === "indexed") && (
                  <li className="flex h-12 items-center gap-3 px-3 animate-in fade-in slide-in-from-top-2 duration-500">
                    <FilePdf className="size-5 shrink-0 text-danger-text" weight="duotone" />
                    <span className="min-w-0 flex-1 truncate font-medium">{FILE}</span>
                    {phase === "indexing" ? (
                      <span className="flex items-center gap-2 text-xs text-muted-foreground"><Spinner className="size-3.5 animate-spin" />Indexing</span>
                    ) : (
                      <span className="flex items-center gap-1.5 text-xs font-medium text-success-text"><CheckCircle weight="fill" className="size-4" />Indexed</span>
                    )}
                  </li>
                )}
                {BASE_ARTICLES.map((title) => (
                  <li key={title} className="flex h-12 items-center justify-between gap-3 px-3 text-muted-foreground"><span className="truncate">{title}</span><span className="text-xs">Article</span></li>
                ))}
              </ul>
              {phase === "dragging" && (
                <div className="pointer-events-none absolute top-[7.5rem] left-1/2 flex -translate-x-1/2 items-center gap-2 rounded-lg border bg-popover px-3 py-2 text-sm shadow-lg animate-in fade-in zoom-in-95 duration-300">
                  <FilePdf className="size-5 text-danger-text" weight="duotone" />{FILE}
                </div>
              )}
            </div>
          ) : (
            <div className="flex h-full flex-col gap-3 p-4 sm:p-5">
              <div className="flex items-start gap-3 animate-in fade-in slide-in-from-bottom-2 duration-500">
                <span className="mt-0.5 grid size-8 shrink-0 place-items-center rounded-full bg-muted text-xs font-medium">MR</span>
                <div className="min-w-0 flex-1 rounded-lg border bg-surface p-3">
                  <p className="text-xs text-muted-foreground">Maya Reyes · just now</p>
                  <p className="mt-1 text-pretty">{QUESTION}</p>
                  <div className="mt-3 flex items-center justify-between gap-2">
                    {phase === "inbound" || phase === "asking" ? (
                      <Button data-target="ask" tabIndex={-1} size="sm" variant="outline" icon={phase === "asking" ? <Spinner className="animate-spin" /> : <Sparkle weight="fill" />}>Ask AI</Button>
                    ) : (
                      <span className="flex items-center gap-1.5 text-xs text-muted-foreground"><Sparkle weight="fill" className="size-3.5" />Asked AI</span>
                    )}
                  </div>
                </div>
              </div>

              {(phase === "context" || phase === "drafting" || phase === "sending" || phase === "sent") && (
                <div className="rounded-lg border border-dashed p-3 animate-in fade-in slide-in-from-bottom-2 duration-500">
                  <p className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground"><FilePdf className="size-3.5" />Context from {FILE}</p>
                  <p className="mt-1 text-pretty text-[0.8125rem]">{CONTEXT}</p>
                </div>
              )}

              {(phase === "drafting" || phase === "sending" || phase === "sent") && (
                <div className="mt-auto flex flex-col gap-2 rounded-lg border p-3 animate-in fade-in slide-in-from-bottom-2 duration-500">
                  <p className="min-h-[4.5rem] text-pretty text-[0.8125rem] leading-relaxed">
                    {DRAFT.slice(0, typed)}
                    {phase === "drafting" && typed < DRAFT.length && <span className="ml-px inline-block h-3.5 w-px translate-y-0.5 bg-foreground" />}
                  </p>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">AI draft · you review before sending</span>
                    {phase === "sent" ? (
                      <span className="flex items-center gap-1.5 text-xs font-medium text-success-text"><CheckCircle weight="fill" className="size-4" />Sent to Maya</span>
                    ) : (
                      <Button data-target="send" tabIndex={-1} size="sm" icon={phase === "sending" ? <Spinner className="animate-spin" /> : <PaperPlaneTilt weight="fill" />} className={cn(phase === "sending" && "translate-y-px")}>Send reply</Button>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Pointer: measured positions, eased like a hand rather than snapped. */}
        {cursor && !STATIC && (
          <svg
            viewBox="0 0 24 24"
            className="pointer-events-none absolute top-0 left-0 size-5 text-foreground drop-shadow transition-transform duration-[900ms] ease-[cubic-bezier(0.16,1,0.3,1)]"
            style={{ transform: `translate(${cursor.x - 3}px, ${cursor.y - 2}px)` }}
          >
            <path d="M4 2l15 9-6.5 1.5L9 19z" fill="currentColor" stroke="var(--background)" strokeWidth="1.5" strokeLinejoin="round" />
          </svg>
        )}
      </div>
    </figure>
  )
}
