import { useNavigate } from '@tanstack/react-router'
import { formatDistanceToNowStrict } from 'date-fns'
import { createContext, useContext, useMemo, useState } from 'react'

import { FilterBar, type FilterDef } from '@/components/patterns/filter-bar'
import { PageHeader } from '@/components/patterns/page-header'
import { CATEGORY_OPTIONS, CategoryLabel, type SelectOption, ChannelLabel, PriorityLabel, SoftBadge, STATUS_OPTIONS, TicketStatusBadge } from '@/components/patterns/ticket-meta'
import { DataTable, type DataColumn } from '@/components/patterns/data-table'
import { Button } from '@/components/ui/button'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Assignee } from '@/components/patterns/assignee'
import { useMembers } from '@/features/workspaces/api'
import { EmptyState, ErrorPanel } from '@/features/app/page-states'
import { useWorkspace } from '@/features/app/workspace-context'
import { NewTicketDialog } from '@/features/tickets/new-ticket-dialog'
import { REAL_PRIORITIES } from '@/features/tickets/options'
import { PAGE_SIZE, useTickets } from '@/features/tickets/api'
import type { TicketSearch } from '@/features/tickets/search'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { ArrowDown, ArrowLeft, ArrowRight, ArrowUp, CalendarBlank, CaretUpDown, CircleHalf, Clock, Flame, FunnelX, Plus, Tag, Ticket as TicketIcon, User, UserCircleDashed } from '@/icons'
import type { TicketSummary } from '@/lib/types'

type OrderState = { ordering: string; toggle: (field: string) => void }
const OrderContext = createContext<OrderState>({ ordering: '-last_activity_at', toggle: () => {} })

function OrderHeader({ label, field }: { label: string; field: string }) {
  const { ordering, toggle } = useContext(OrderContext)
  const active = ordering.replace(/^-/, '') === field
  const desc = ordering.startsWith('-')
  return (
    <Button
      variant="ghost"
      size="xs"
      className="-ml-2 text-muted-foreground hover:text-foreground"
      iconEnd={active ? (desc ? <ArrowDown weight="bold" /> : <ArrowUp weight="bold" />) : <CaretUpDown />}
      onClick={() => toggle(field)}
      aria-label={`Sort by ${label}`}
    >
      {label}
    </Button>
  )
}

// Module scope: TanStack Table needs stable columns. Ordering is server-side, so headers read it from context.
const columns: DataColumn<TicketSummary>[] = [
  { id: 'number', header: () => <OrderHeader label="Ticket" field="number" />, enableSorting: false, enableHiding: false, cell: ({ row }) => <span className="tabular-nums text-muted-foreground">#{row.original.number}</span> },
  {
    id: 'subject',
    header: 'Subject',
    enableHiding: false,
    meta: { label: 'Subject' },
    cell: ({ row }) => (
      <span className="flex items-center gap-2">
        <span className="truncate font-medium" title={row.original.subject}>{row.original.subject}</span>
        {row.original.waiting_for_reply && <SoftBadge tone="warning" icon={Clock}>Waiting</SoftBadge>}
      </span>
    ),
  },
  { id: 'status', header: () => <OrderHeader label="Status" field="status" />, enableSorting: false, cell: ({ row }) => <TicketStatusBadge status={row.original.status} /> },
  { id: 'priority', header: () => <OrderHeader label="Priority" field="priority" />, enableSorting: false, cell: ({ row }) => <PriorityLabel priority={row.original.priority} /> },
  { id: 'category', header: 'Category', enableSorting: false, cell: ({ row }) => <CategoryLabel category={row.original.category} /> },
  { id: 'source', header: 'Source', enableSorting: false, cell: ({ row }) => <ChannelLabel channel={row.original.created_via} /> },
  { id: 'assignee', header: 'Assignee', enableSorting: false, cell: ({ row }) => <span className="truncate text-sm"><Assignee name={row.original.assignee?.display_name} /></span> },
  { id: 'customer', header: 'Customer', enableSorting: false, cell: ({ row }) => <span className="truncate" title={row.original.customer_email}>{row.original.customer_name || row.original.customer_email}</span> },
  { id: 'activity', header: () => <OrderHeader label="Last activity" field="last_activity_at" />, enableSorting: false, cell: ({ row }) => <span className="text-muted-foreground" title={row.original.last_activity_at}>{formatDistanceToNowStrict(new Date(row.original.last_activity_at), { addSuffix: true })}</span> },
]

export function TicketsPage({ search }: { search: TicketSearch }) {
  useDocumentTitle('Tickets · ResolveAI')
  const { workspace } = useWorkspace()
  const navigate = useNavigate()
  const [creating, setCreating] = useState(false)
  const tickets = useTickets(workspace.id, search)
  const ordering = search.ordering ?? '-last_activity_at'

  const update = (patch: Partial<TicketSearch>) =>
    void navigate({ to: '.', search: ((prev: TicketSearch) => ({ ...prev, ...patch, page: 'page' in patch ? patch.page : undefined })) as never, replace: true })

  const order = useMemo<OrderState>(
    () => ({ ordering, toggle: (field) => update({ ordering: ordering === field ? `-${field}` : field }) }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [ordering],
  )

  const members = useMembers(workspace.id)
  const assigneeOptions = useMemo<SelectOption[]>(
    () => [{ value: 'me', label: 'Me', icon: User }, { value: 'unassigned', label: 'Unassigned', icon: UserCircleDashed }, ...(members.data ?? []).map((m) => ({ value: m.user_id, label: m.display_name }))],
    [members.data],
  )
  const filters: FilterDef[] = [
    { id: 'status', kind: 'select', label: 'Status', icon: CircleHalf, options: STATUS_OPTIONS, value: search.status, onChange: (v) => update({ status: v as TicketSearch['status'] }) },
    { id: 'priority', kind: 'select', label: 'Priority', icon: Flame, options: REAL_PRIORITIES, value: search.priority, onChange: (v) => update({ priority: v as TicketSearch['priority'] }) },
    { id: 'category', kind: 'select', label: 'Category', icon: Tag, options: CATEGORY_OPTIONS, value: search.category, onChange: (v) => update({ category: v as TicketSearch['category'] }) },
    { id: 'assignee', kind: 'select', label: 'Assigned to', icon: User, options: assigneeOptions, value: search.assignee, onChange: (v) => update({ assignee: v }) },
    { id: 'created', kind: 'date-range', label: 'Created', icon: CalendarBlank, value: { from: search.created_from, to: search.created_to }, onChange: (r) => update({ created_from: r.from, created_to: r.to }) },
    { id: 'waiting', kind: 'boolean', label: 'Waiting for reply', icon: Clock, value: search.waiting_for_reply, onChange: (v) => update({ waiting_for_reply: v ? true : undefined }) },
  ]
  const mine = search.assignee === 'me'

  const filtered = Boolean(search.assignee || search.status || search.priority || search.category || search.created_from || search.created_to || search.q || search.waiting_for_reply)
  const page = search.page ?? 1
  const count = tickets.data?.meta.count ?? 0
  const from = count === 0 ? 0 : (page - 1) * PAGE_SIZE + 1
  const to = Math.min(count, page * PAGE_SIZE)

  return (
    <div className="space-y-5">
      <PageHeader title="Tickets" description="Everything customers asked for, from email and the portal." actions={<Button icon={<Plus />} onClick={() => setCreating(true)}>New ticket</Button>} />
      <Tabs value={mine ? 'mine' : 'all'} onValueChange={(v) => update({ assignee: v === 'mine' ? 'me' : search.assignee === 'me' ? undefined : search.assignee })}>
        <TabsList aria-label="Ticket scope">
          <TabsTrigger value="all"><TicketIcon />All tickets</TabsTrigger>
          <TabsTrigger value="mine"><User />My tickets</TabsTrigger>
        </TabsList>
      </Tabs>
      <FilterBar
        search={{ value: search.q ?? '', onCommit: (q) => update({ q }), placeholder: 'Search subject or customer' }}
        filters={filters}
        onClearAll={() => void navigate({ to: '.', search: {} as never, replace: true })}
      />

      {tickets.error ? (
        <ErrorPanel error={tickets.error} onRetry={() => void tickets.refetch()} title="Tickets could not be loaded" />
      ) : (
        <OrderContext.Provider value={order}>
          <DataTable
            columns={columns}
            data={tickets.data?.items ?? EMPTY}
            getRowId={(t) => t.id}
            caption="Tickets"
            loading={tickets.isPending}
            onRowClick={(t) => void navigate({ to: `/app/${workspace.id}/tickets/${t.id}` as never })}
            empty={
              filtered ? (
                <EmptyState icon={TicketIcon} title="No tickets match these filters" action={<Button variant="outline" icon={<FunnelX />} onClick={() => void navigate({ to: '.', search: {} as never, replace: true })}>Clear filters</Button>}>Try fewer filters or a different search.</EmptyState>
              ) : (
                <EmptyState icon={TicketIcon} title="No tickets yet" action={<Button icon={<Plus />} onClick={() => setCreating(true)}>New ticket</Button>}>New tickets from email and the portal show up here.</EmptyState>
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
      <NewTicketDialog workspaceId={workspace.id} open={creating} onOpenChange={setCreating} />
    </div>
  )
}

const EMPTY: TicketSummary[] = []
