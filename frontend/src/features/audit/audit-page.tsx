import { useNavigate } from '@tanstack/react-router'
import { formatDistanceToNowStrict } from 'date-fns'

import { FilterBar } from '@/components/patterns/filter-bar'
import { PageHeader } from '@/components/patterns/page-header'
import { SoftBadge } from '@/components/patterns/ticket-meta'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState, ErrorPanel } from '@/features/app/page-states'
import { useWorkspace } from '@/features/app/workspace-context'
import { AUDIT_PAGE_SIZE, useAuditEvents, type AuditEvent } from '@/features/audit/api'
import { GROUPS, type AuditSearch } from '@/features/audit/search'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { ArrowLeft, ArrowRight, CalendarBlank, ClockCounterClockwise, LockSimple, Shapes } from '@/icons'
import { formatDateTime } from '@/lib/format'

const label = (action: string) => action.replace(/[._]/g, ' ').replace(/^\w/, (c) => c.toUpperCase())

function metadataText(metadata: Record<string, unknown>): string {
  return Object.entries(metadata).map(([k, v]) => `${k.replace(/_/g, ' ')}: ${String(v)}`).join(' · ')
}

function Row({ event }: { event: AuditEvent }) {
  const meta = metadataText(event.metadata)
  return (
    <li className="flex flex-wrap items-start gap-x-4 gap-y-1 p-3">
      <div className="min-w-0 flex-1 space-y-0.5">
        <p className="flex flex-wrap items-center gap-2 text-sm font-medium">{label(event.action)}{event.target && <SoftBadge>{event.target.type}</SoftBadge>}</p>
        <p className="text-xs text-muted-foreground">{event.actor ? `By ${event.actor.name || 'a former member'}` : 'By the system'}{meta ? ` · ${meta}` : ''}</p>
      </div>
      <time className="text-xs text-muted-foreground" dateTime={event.created_at} title={formatDateTime(event.created_at)}>{formatDistanceToNowStrict(new Date(event.created_at), { addSuffix: true })}</time>
    </li>
  )
}

export function AuditPage({ search }: { search: AuditSearch }) {
  useDocumentTitle('Audit log · ResolveAI')
  const { workspace, isOwner } = useWorkspace()
  const navigate = useNavigate()
  const events = useAuditEvents(workspace.id, search, isOwner)
  const update = (patch: Partial<AuditSearch>) =>
    void navigate({ to: '.', search: ((prev: AuditSearch) => ({ ...prev, ...patch, page: 'page' in patch ? patch.page : undefined })) as never, replace: true })

  if (!isOwner) {
    return (
      <div className="mx-auto max-w-2xl space-y-5">
        <PageHeader title="Audit log" />
        <EmptyState icon={LockSimple} title="Only the owner can read the audit log">Ask the workspace owner if you need something from it.</EmptyState>
      </div>
    )
  }

  const filtered = Boolean(search.action_prefix || search.created_from || search.created_to)
  const page = search.page ?? 1
  const count = events.data?.meta.count ?? 0
  const to = Math.min(count, page * AUDIT_PAGE_SIZE)
  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <PageHeader title="Audit log" description="Sensitive actions in this workspace, newest first. Message text and secrets are never recorded." />
      <FilterBar
        filters={[
          { id: 'area', kind: 'select', label: 'Area', icon: Shapes, options: GROUPS, value: search.action_prefix, onChange: (v) => update({ action_prefix: v }) },
          { id: 'between', kind: 'date-range', label: 'Between', icon: CalendarBlank, value: { from: search.created_from, to: search.created_to }, onChange: (r) => update({ created_from: r.from, created_to: r.to }) },
        ]}
        onClearAll={() => void navigate({ to: '.', search: {} as never, replace: true })}
      />
      {events.error ? (
        <ErrorPanel error={events.error} onRetry={() => void events.refetch()} />
      ) : events.isPending ? (
        <div className="space-y-2" aria-busy="true" aria-label="Loading">{Array.from({ length: 6 }, (_, i) => <Skeleton key={i} className="h-12 w-full" />)}</div>
      ) : events.data.items.length === 0 ? (
        <EmptyState icon={ClockCounterClockwise} title={filtered ? 'Nothing matches these filters' : 'Nothing recorded yet'}>Actions like inviting a member or changing a ticket's status appear here.</EmptyState>
      ) : (
        <>
          <ul className="divide-y rounded-xl border">{events.data.items.map((e) => <Row key={e.id} event={e} />)}</ul>
          <div className="flex items-center justify-between gap-3 text-sm text-muted-foreground">
            <span className="tabular-nums">{(page - 1) * AUDIT_PAGE_SIZE + 1}–{to} of {count}</span>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" icon={<ArrowLeft />} disabled={page <= 1} onClick={() => update({ page: page - 1 || undefined })}>Previous</Button>
              <Button variant="outline" size="sm" iconEnd={<ArrowRight />} disabled={to >= count} onClick={() => update({ page: page + 1 })}>Next</Button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
