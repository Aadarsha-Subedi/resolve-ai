import { formatDistanceToNowStrict } from 'date-fns'
import { useEffect, useState, type ReactNode } from 'react'

import { hitSource, splitCitations, type Answer, type AskTurn, type Claim } from '@/features/ai/context-api'
import { ContextResults } from '@/features/ai/context-panel'
import { ErrorPanel } from '@/features/app/page-states'
import { Quotes, Robot, SealCheck } from '@/icons'
import { cn } from '@/lib/utils'

/** What the agent is "doing" while a question is answered; one is shown at a time. */
export const THINKING_VERBS = [
  'Thinking',
  'Reading the sources',
  'Cross-checking the sources',
  'Connecting the dots',
  'Piecing it together',
  'Weighing the details',
  'Drafting an answer',
  'Double-checking',
]
const VERB_MS = 2400

export function AgentAvatar({ className }: { className?: string }) {
  return (
    <span aria-hidden className={cn('flex size-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary', className)}>
      <Robot weight="fill" className="size-4.5" />
    </span>
  )
}

function AgentRow({ children, label, time }: { children: ReactNode; label?: string; time?: string }) {
  return (
    <div className="flex items-start gap-3">
      <AgentAvatar />
      <div className="min-w-0 max-w-[85%] space-y-1">
        <p className="flex items-baseline gap-2 text-xs text-muted-foreground"><span className="font-medium text-foreground">{label ?? 'Resolve AI'}</span>{time && <time dateTime={time} title={new Date(time).toLocaleString()}>{formatDistanceToNowStrict(new Date(time), { addSuffix: true })}</time>}</p>
        <div className="rounded-2xl rounded-tl-sm border bg-card px-4 py-3">{children}</div>
      </div>
    </div>
  )
}

export function UserBubble({ children, time }: { children: ReactNode; time?: string }) {
  return (
    <div className="flex flex-col items-end gap-1">
      <p className="max-w-[85%] rounded-2xl rounded-br-sm bg-primary px-4 py-2 text-sm text-primary-foreground whitespace-pre-wrap [overflow-wrap:anywhere]">{children}</p>
      {time && <time className="text-xs text-muted-foreground" dateTime={time}>{formatDistanceToNowStrict(new Date(time), { addSuffix: true })}</time>}
    </div>
  )
}

/** The agent's "typing" bubble: a changing verb and three pulsing dots (still when the user prefers less motion). */
export function Thinking() {
  const [i, setI] = useState(0)
  useEffect(() => {
    const id = window.setInterval(() => setI((n) => (n + 1) % THINKING_VERBS.length), VERB_MS)
    return () => window.clearInterval(id)
  }, [])
  return (
    <AgentRow>
      <p role="status" aria-live="polite" className="flex items-center gap-2 text-sm text-muted-foreground">
        <span>{THINKING_VERBS[i]}</span>
        <span aria-hidden className="flex gap-0.5">
          {[0, 150, 300].map((d) => <span key={d} style={{ animationDelay: `${d}ms` }} className="size-1 rounded-full bg-current motion-safe:animate-bounce" />)}
        </span>
      </p>
    </AgentRow>
  )
}

function AnswerText({ answer, prefix, onCite }: { answer: Answer; prefix: string; onCite: (n: number) => void }) {
  return (
    <p className="text-sm leading-relaxed whitespace-pre-wrap [overflow-wrap:anywhere]">
      {splitCitations(answer.answer ?? '', answer.results.length).map((part, i) =>
        part.cite ? <a key={i} href={`#${prefix}-${part.cite}`} onClick={(e) => { e.preventDefault(); onCite(part.cite!) }} className="font-medium tabular-nums text-primary underline-offset-2 hover:underline">{part.text}</a> : <span key={i}>{part.text}</span>,
      )}
    </p>
  )
}

/** The answer as separate claims. A numbered badge opens the exact words found in that source. */
function ClaimsList({ answer, prefix, onCite }: { answer: Answer & { claims: Claim[] }; prefix: string; onCite: (n: number) => void }) {
  const [open, setOpen] = useState<string | null>(null)
  return (
    <div className="space-y-3">
      <ul className="space-y-3">
        {answer.claims.map((claim, i) => (
          <li key={i} className="space-y-1.5">
            <p className="text-sm leading-relaxed [overflow-wrap:anywhere]">
              {claim.text}{' '}
              {claim.cites.map((cite, j) => {
                const id = `${i}-${j}`
                return (
                  <button key={id} type="button" aria-expanded={open === id} aria-label={`Show the quote from source ${cite.n}`} onClick={() => setOpen(open === id ? null : id)} className="mr-0.5 inline-flex items-center gap-0.5 rounded-sm px-1 align-baseline text-xs font-medium tabular-nums text-primary hover:bg-primary/10">
                    <SealCheck aria-hidden weight="fill" className="size-3" />[{cite.n}]
                  </button>
                )
              })}
            </p>
            {claim.cites.map((cite, j) => {
              if (open !== `${i}-${j}`) return null
              const hit = answer.results[cite.n - 1]
              const source = hit ? hitSource(hit) : null
              return (
                <blockquote key={j} className="space-y-1 rounded-md border-l-2 border-primary/50 bg-muted/40 px-3 py-2">
                  <p className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground"><Quotes aria-hidden className="size-3.5" />Found in source {cite.n}{source ? `: ${source.title}${source.page ? `, page ${source.page}` : ''}` : ''}</p>
                  <p className="text-sm leading-relaxed whitespace-pre-wrap [overflow-wrap:anywhere]">
                    {cite.before && <span className="text-muted-foreground">…{cite.before}</span>}
                    <mark className="rounded-sm bg-primary/15 px-0.5 text-foreground">{cite.quote}</mark>
                    {cite.after && <span className="text-muted-foreground">{cite.after}…</span>}
                  </p>
                  <button type="button" onClick={() => onCite(cite.n)} className="text-xs font-medium text-primary underline-offset-2 hover:underline">Show source {cite.n}</button>
                </blockquote>
              )
            })}
          </li>
        ))}
      </ul>
      <p id={`${prefix}-verified`} className="text-xs text-muted-foreground">Each quote was checked against the source text. This confirms the words are in the source, not that the statement is correct. Open a quote to read it in place.</p>
    </div>
  )
}

/** Why an answer could not be written, by the backend's error code. The matching articles are always still shown. */
const UNAVAILABLE_REASONS: Record<string, string> = {
  llm_insufficient_quota: 'Your AI provider account has no credit or quota left. Add credit with your provider, then ask again.',
  llm_rate_limited: 'Your AI provider is rate limiting requests. Wait a minute and ask again.',
  llm_invalid_key: 'Your API key was rejected. Replace it in Settings, AI assistant.',
  llm_timeout: 'The AI provider took too long to answer. Try again.',
}
const UNAVAILABLE_DEFAULT = 'An answer could not be written right now.'

const NOTES = {
  not_covered: 'No verified answer. No statement could be backed by a quote from the sources found. They are listed below in case they help.',
  no_results: 'No matching articles or documents. Only published articles and uploaded files that have been read are searched, so try different words.',
} as const

/** One finished exchange: the question on the right, the agent's answer and its numbered sources on the left. */
export function TurnView({ workspaceId, turn }: { workspaceId: string; turn: AskTurn }) {
  const prefix = `src-${turn.turn_id}`
  const [sourcesOpen, setSourcesOpen] = useState(false)
  // A [n] marker opens the collapsed list, then scrolls to that source once it is visible.
  const showSource = (n: number) => {
    setSourcesOpen(true)
    window.requestAnimationFrame(() => document.getElementById(`${prefix}-${n}`)?.scrollIntoView?.({ block: 'center', behavior: 'smooth' }))
  }
  return (
    <li className="space-y-4">
      <UserBubble time={turn.created_at}>{turn.question}</UserBubble>
      <AgentRow>
        <div className="space-y-3">
          {turn.status === 'answered' ? (turn.claims && turn.claims.length > 0 ? <ClaimsList answer={{ ...turn, claims: turn.claims }} prefix={prefix} onCite={showSource} /> : <AnswerText answer={turn} prefix={prefix} onCite={showSource} />) : <p className="text-sm text-muted-foreground">{turn.status === 'unavailable' ? `${(turn.reason && UNAVAILABLE_REASONS[turn.reason]) || UNAVAILABLE_DEFAULT} These are the matching sources.` : NOTES[turn.status]}</p>}
          {turn.results.length > 0 && (
            <details open={sourcesOpen} onToggle={(e) => setSourcesOpen(e.currentTarget.open)} className="border-t pt-2">
              <summary className="cursor-pointer text-xs font-medium text-muted-foreground">Sources ({turn.results.length})</summary>
              <ContextResults workspaceId={workspaceId} result={turn} idPrefix={prefix} />
            </details>
          )}
        </div>
      </AgentRow>
    </li>
  )
}

/** A question that is being answered, or failed to be. */
export function PendingTurn({ question, error, onRetry }: { question: string; error?: unknown; onRetry?: () => void }) {
  return (
    <li className="space-y-4">
      <UserBubble>{question}</UserBubble>
      {error ? <div className="pl-11"><ErrorPanel error={error} onRetry={onRetry} title="This question could not be answered" /></div> : <Thinking />}
    </li>
  )
}
