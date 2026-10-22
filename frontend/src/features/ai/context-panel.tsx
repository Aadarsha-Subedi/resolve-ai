import { Link } from '@tanstack/react-router'

import { EmptyState, ErrorPanel, LinesSkeleton } from '@/features/app/page-states'
import { splitHighlights, type ContextHit, type ContextResult, type useTicketContext } from '@/features/ai/context-api'
import { Books, MagnifyingGlass } from '@/icons'

export function Snippet({ text }: { text: string }) {
  return (
    <p className="text-sm leading-relaxed [overflow-wrap:anywhere]">
      {splitHighlights(text).map((part, i) => part.hit ? <mark key={i} className="rounded-sm bg-primary/15 px-0.5 text-foreground">{part.text}</mark> : <span key={i}>{part.text}</span>)}
    </p>
  )
}

function Hit({ workspaceId, hit, idPrefix }: { workspaceId: string; hit: ContextHit; idPrefix?: string }) {
  return (
    <li id={idPrefix ? `${idPrefix}-${hit.citation}` : undefined} className="scroll-mt-20 space-y-1 py-3">
      <div className="flex items-baseline gap-2">
        <span className="text-xs font-medium tabular-nums text-muted-foreground" aria-label={`Source ${hit.citation}`}>[{hit.citation}]</span>
        <Link to={`/app/${workspaceId}/knowledge/${hit.article.id}` as never} className="min-w-0 text-sm font-medium underline-offset-4 hover:underline [overflow-wrap:anywhere]">{hit.article.title}</Link>
      </div>
      {hit.section && <p className="text-xs text-muted-foreground [overflow-wrap:anywhere]">{hit.section}</p>}
      <Snippet text={hit.snippet} />
    </li>
  )
}

/** `idPrefix` gives each passage an anchor (`<prefix>-<n>`) so an answer's [n] markers can jump to it. */
export function ContextResults({ workspaceId, result, idPrefix }: { workspaceId: string; result: ContextResult; idPrefix?: string }) {
  if (result.results.length === 0) {
    return <EmptyState icon={MagnifyingGlass} title="No matching articles">Only published articles are searched. Try the question box with different words.</EmptyState>
  }
  return (
    <div className="space-y-2">
      <ol className="divide-y">{result.results.map((hit) => <Hit key={hit.chunk_id} workspaceId={workspaceId} hit={hit} idPrefix={idPrefix} />)}</ol>
      <p className="text-xs text-muted-foreground [overflow-wrap:anywhere]">
        {result.rewritten ? <>Searched with: {result.queries.map((q, i) => <span key={i}>{i > 0 && ' · '}“{q.length > 80 ? `${q.slice(0, 80)}…` : q}”</span>)}</> : 'Searched with your exact words. Rewriting the question was not possible this time.'}
      </p>
    </div>
  )
}

/** Right-hand "Related articles" panel of the ticket page: the result of the last "Find context" click. */
export function ContextPanel({ workspaceId, ticketSearch }: { workspaceId: string; ticketSearch: ReturnType<typeof useTicketContext> }) {
  const source = ticketSearch.variables ? 'The customer message' : 'This ticket'
  return (
    <section aria-labelledby="ctx" className="space-y-3">
      <h2 id="ctx" className="flex items-center gap-2 text-sm font-semibold"><Books className="size-4 text-muted-foreground" aria-hidden />Related articles</h2>
      <div aria-live="polite" aria-busy={ticketSearch.isPending}>
        {ticketSearch.isPending ? <LinesSkeleton rows={3} />
          : ticketSearch.error ? <ErrorPanel error={ticketSearch.error} title="Search failed" />
          : ticketSearch.data ? <><p className="pb-1 text-xs text-muted-foreground">{source}</p><ContextResults workspaceId={workspaceId} result={ticketSearch.data} /></>
          : <p className="text-sm text-muted-foreground">Use “Find context” on the ticket or on a customer message to see matching articles.</p>}
      </div>
    </section>
  )
}
