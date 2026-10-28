import { useNavigate } from '@tanstack/react-router'
import { formatDistanceToNowStrict } from 'date-fns'
import { createContext, useContext, useMemo, useState } from 'react'

import { DataTable, type DataColumn } from '@/components/patterns/data-table'
import { FilterBar, type FilterDef } from '@/components/patterns/filter-bar'
import { PageHeader } from '@/components/patterns/page-header'
import { SoftBadge, type SelectOption, type Tone } from '@/components/patterns/ticket-meta'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { USAGE_PAGE_SIZE, useAiUsage, type UsageLog, type UsageOutcome, type UsageSearch } from '@/features/ai/usage-api'
import { FEATURE_LABELS, OUTCOME_LABELS } from '@/features/ai/usage-search'
import { EmptyState, ErrorPanel } from '@/features/app/page-states'
import { useWorkspace } from '@/features/app/workspace-context'
import { useMembers } from '@/features/workspaces/api'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { ArrowDown, ArrowLeft, ArrowRight, ArrowUp, CalendarBlank, CaretUpDown, CircleHalf, ClockCounterClockwise, FunnelX, LockSimple, Shapes, User } from '@/icons'
import { formatDateTime } from '@/lib/format'

const OUTCOME_TONE: Record<UsageOutcome, Tone> = { cache_hit: 'success', llm_call: 'info', error: 'danger' }
const FEATURE_OPTIONS: SelectOption[] = Object.entries(FEATURE_LABELS).map(([value, label]) => ({ value, label }))
const OUTCOME_OPTIONS: SelectOption[] = Object.entries(OUTCOME_LABELS).map(([value, label]) => ({ value, label }))
const EMPTY: UsageLog[] = []

type OrderState = { ordering: string; toggle: (field: string) => void }
const OrderContext = createContext<OrderState>({ ordering: '-created_at', toggle: () => {} })

function OrderHeader({ label, field }: { label: string; field: string }) {
  const { ordering, toggle } = useContext(OrderContext)
  const active = ordering.replace(/^-/, '') === field
  return (
    <Button
      variant="ghost"
      size="xs"
      className="-ml-2 text-muted-foreground hover:text-foreground"
      iconEnd={active ? (ordering.startsWith('-') ? <ArrowDown weight="bold" /> : <ArrowUp weight="bold" />) : <CaretUpDown />}
      onClick={() => toggle(field)}
      aria-label={`Sort by ${label}`}
    >
      {label}
    </Button>
  )
}

function OutcomeBadge({ outcome }: { outcome: UsageOutcome }) {
  return <SoftBadge tone={OUTCOME_TONE[outcome]}>{OUTCOME_LABELS[outcome]}</SoftBadge>
}

const tokens = (row: UsageLog) => row.input_tokens + row.output_tokens

// Module scope: TanStack Table needs stable columns. Ordering is server-side, so headers read it from context.
const columns: DataColumn<UsageLog>[] = [
  { id: 'time', header: () => <OrderHeader label="Time" field="created_at" />, enableSorting: false, enableHiding: false, cell: ({ row }) => <span className="whitespace-nowrap text-muted-foreground" title={formatDateTime(row.original.created_at)}>{formatDistanceToNowStrict(new Date(row.original.created_at), { addSuffix: true })}</span> },
  { id: 'user', header: () => <OrderHeader label="User" field="user" />, enableSorting: false, cell: ({ row }) => <span className="truncate">{row.original.user?.name ?? 'Former member'}</span> },
  { id: 'feature', header: () => <OrderHeader label="Type" field="feature" />, enableSorting: false, cell: ({ row }) => FEATURE_LABELS[row.original.feature] },
  { id: 'outcome', header: () => <OrderHeader label="Result" field="outcome" />, enableSorting: false, cell: ({ row }) => <OutcomeBadge outcome={row.original.outcome} /> },
  { id: 'question', header: 'Question', enableHiding: false, meta: { label: 'Question' }, cell: ({ row }) => <span className="block max-w-md truncate font-medium" title={row.original.question}>{row.original.question || '—'}</span> },
  { id: 'tokens', header: () => <OrderHeader label="Tokens" field="tokens" />, enableSorting: false, cell: ({ row }) => <span className="tabular-nums text-muted-foreground">{tokens(row.original) || '—'}</span> },
]

function Detail({ log, onClose }: { log: UsageLog | null; onClose: () => void }) {
  const passages = log?.details.passages ?? []
  return (
    <Dialog open={log !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-2xl">
        {log && (
          <>
            <DialogHeader>
              <DialogTitle>{FEATURE_LABELS[log.feature]}</DialogTitle>
              <DialogDescription>
                {formatDateTime(log.created_at)} · {log.user?.name ?? 'Former member'}
                {log.model ? ` · ${log.model}` : ''}
              </DialogDescription>
            </DialogHeader>
            <div className="max-h-[60vh] space-y-4 overflow-y-auto text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <OutcomeBadge outcome={log.outcome} />
                {log.details.similarity != null && <span className="text-muted-foreground tabular-nums">Matched a cached question at {(log.details.similarity * 100).toFixed(1)}% similarity</span>}
                {tokens(log) > 0 && <span className="text-muted-foreground tabular-nums">{log.input_tokens} in · {log.output_tokens} out tokens</span>}
                {log.error_code && <span className="text-danger-text">{log.error_code}</span>}
              </div>
              <section aria-labelledby="usage-question">
                <h3 id="usage-question" className="mb-1 text-xs font-medium text-muted-foreground">Question</h3>
                <p className="whitespace-pre-wrap">{log.question || '—'}</p>
              </section>
              {log.details.cached_question && log.details.cached_question !== log.question && (
                <section aria-labelledby="usage-cached">
                  <h3 id="usage-cached" className="mb-1 text-xs font-medium text-muted-foreground">Cached question it matched</h3>
                  <p className="whitespace-pre-wrap">{log.details.cached_question}</p>
                </section>
              )}
              {log.answer && (
                <section aria-labelledby="usage-answer">
                  <h3 id="usage-answer" className="mb-1 text-xs font-medium text-muted-foreground">{log.feature === 'ask' ? 'Answer' : 'Result'}</h3>
                  <p className="whitespace-pre-wrap">{log.answer}</p>
                </section>
              )}
              {passages.length > 0 && (
                <section aria-labelledby="usage-passages">
                  <h3 id="usage-passages" className="mb-1 text-xs font-medium text-muted-foreground">Passages the AI read</h3>
                  <ul className="divide-y rounded-lg border">
                    {passages.map((p) => (
                      <li key={p.citation} className="flex items-baseline justify-between gap-3 px-3 py-2">
                        <span className="min-w-0 truncate"><span className="tabular-nums text-muted-foreground">[{p.citation}]</span> {p.title}{p.section ? ` · ${p.section}` : ''}{p.page ? ` (page ${p.page})` : ''}</span>
                        {p.cited && <SoftBadge tone="success" icon={null}>Cited</SoftBadge>}
                      </li>
                    ))}
                  </ul>
                </section>
              )}
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}

/** Owner-only log of every AI call in the workspace: answered from the cache, sent to the AI provider, or failed. */
export function UsagePage({ search }: { search: UsageSearch }) {
  useDocumentTitle('AI usage log · ResolveAI')
  const { workspace, isOwner } = useWorkspace()
  const navigate = useNavigate()
  const [open, setOpen] = useState<UsageLog | null>(null)
  const usage = useAiUsage(workspace.id, search, isOwner)
  const members = useMembers(workspace.id)
  const ordering = search.ordering ?? '-created_at'

  const update = (patch: Partial<UsageSearch>) =>
    void navigate({ to: '.', search: ((prev: UsageSearch) => ({ ...prev, ...patch, page: 'page' in patch ? patch.page : undefined })) as never, replace: true })
  const clearAll = () => void navigate({ to: '.', search: {} as never, replace: true })

  const order = useMemo<OrderState>(
    () => ({ ordering, toggle: (field) => update({ ordering: ordering === field ? `-${field}` : field }) }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [ordering],
  )
  const memberOptions = useMemo<SelectOption[]>(() => (members.data ?? []).map((m) => ({ value: m.user_id, label: m.display_name })), [members.data])

  if (!isOwner) {
    return (
      <div className="mx-auto max-w-2xl space-y-5">
        <PageHeader title="AI usage log" />
        <EmptyState icon={LockSimple} title="Only the owner can read the AI usage log">Ask the workspace owner if you need something from it.</EmptyState>
      </div>
    )
  }

  const filters: FilterDef[] = [
    { id: 'feature', kind: 'select', label: 'Type', icon: Shapes, options: FEATURE_OPTIONS, value: search.feature, onChange: (v) => update({ feature: v as UsageSearch['feature'] }) },
    { id: 'outcome', kind: 'select', label: 'Result', icon: CircleHalf, options: OUTCOME_OPTIONS, value: search.outcome, onChange: (v) => update({ outcome: v as UsageSearch['outcome'] }) },
    { id: 'actor', kind: 'select', label: 'User', icon: User, options: memberOptions, value: search.actor, onChange: (v) => update({ actor: v }) },
    { id: 'between', kind: 'date-range', label: 'Between', icon: CalendarBlank, value: { from: search.created_from, to: search.created_to }, onChange: (r) => update({ created_from: r.from, created_to: r.to }) },
  ]
  const filtered = Boolean(search.q || search.feature || search.outcome || search.actor || search.created_from || search.created_to)
  const summary = usage.data?.meta.summary
  const page = search.page ?? 1
  const count = usage.data?.meta.count ?? 0
  const from = count === 0 ? 0 : (page - 1) * USAGE_PAGE_SIZE + 1
  const to = Math.min(count, page * USAGE_PAGE_SIZE)

  return (
    <div className="space-y-5">
      <PageHeader
        title="AI usage log"
        description={
          summary && summary.hit_rate !== null
            ? `${summary.cache_hits} of ${summary.cache_hits + summary.llm_calls} answered calls came from the cache (${Math.round(summary.hit_rate * 100)}%). ${summary.llm_calls} were sent to the AI${summary.errors ? `, ${summary.errors} failed` : ''}.`
            : 'Every AI call in this workspace: answered from the cache or sent to the AI provider.'
        }
      />
      <FilterBar
        search={{ value: search.q ?? '', onCommit: (q) => update({ q }), placeholder: 'Search question, answer or user' }}
        filters={filters}
        onClearAll={clearAll}
      />
      {usage.error ? (
        <ErrorPanel error={usage.error} onRetry={() => void usage.refetch()} title="The usage log could not be loaded" />
      ) : (
        <OrderContext.Provider value={order}>
          <DataTable
            columns={columns}
            data={usage.data?.items ?? EMPTY}
            getRowId={(r) => r.id}
            caption="AI usage log"
            loading={usage.isPending}
            onRowClick={setOpen}
            empty={
              filtered ? (
                <EmptyState icon={ClockCounterClockwise} title="Nothing matches these filters" action={<Button variant="outline" icon={<FunnelX />} onClick={clearAll}>Clear filters</Button>}>Try fewer filters or a different search.</EmptyState>
              ) : (
                <EmptyState icon={ClockCounterClockwise} title="No AI calls yet">Questions asked on the Ask page appear here, with the answer and whether it came from the cache.</EmptyState>
              )
            }
            footer={
              count > 0 ? (
                <div className="flex items-center justify-between gap-3 text-sm text-muted-foreground">
                  <span className="tabular-nums">{from}–{to} of {count}</span>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" icon={<ArrowLeft />} disabled={page <= 1} onClick={() => update({ page: page - 1 || undefined })}>Previous</Button>
                    <Button variant="outline" size="sm" iconEnd={<ArrowRight />} disabled={to >= count} onClick={() => update({ page: page + 1 })}>Next</Button>
                  </div>
                </div>
              ) : null
            }
          />
        </OrderContext.Provider>
      )}
      <Detail log={open} onClose={() => setOpen(null)} />
    </div>
  )
}
