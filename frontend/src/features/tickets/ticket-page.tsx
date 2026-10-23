import { Link } from '@tanstack/react-router'
import { useState } from 'react'
import { toast } from 'sonner'

import { OptionSelect } from '@/components/patterns/option-select'
import { PropertyRow } from '@/components/patterns/property-row'
import { Restricted } from '@/components/patterns/restricted'
import { CATEGORY_OPTIONS, ChannelLabel, SoftBadge, STATUS_OPTIONS, TicketStatusBadge, type SelectOption } from '@/components/patterns/ticket-meta'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ErrorPanel } from '@/features/app/page-states'
import { useWorkspace } from '@/features/app/workspace-context'
import { useAssignTicket, useChangeStatus, useTicketOverview, useUpdateTicket } from '@/features/tickets/api'
import { DraftReplyDialog, SummarySection } from '@/features/tickets/ai-actions'
import { Conversation } from '@/features/tickets/conversation'
import { EditTicketDialog } from '@/features/tickets/edit-ticket-dialog'
import { REAL_PRIORITIES } from '@/features/tickets/options'
import { HistoryDialog } from '@/features/tickets/history-dialog'
import { useMembers } from '@/features/workspaces/api'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { ArrowLeft, Clock, MagicWand, ClockCounterClockwise, DotsThreeVertical, PencilSimple, User, UserCircleDashed } from '@/icons'
import { ApiError, errorMessage } from '@/lib/api'
import { formatDateTime } from '@/lib/format'
import type { TicketCategoryValue, TicketPriorityValue, TicketStatusValue } from '@/lib/types'

const UNASSIGNED = '__unassigned'
const REOPEN_ONLY_OWNER = 'Only the workspace owner can change a closed ticket.'

function PageSkeleton() {
  return (
    <div className="space-y-5" aria-busy="true" aria-label="Loading ticket">
      <Skeleton className="h-8 w-80" />
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="space-y-3">{Array.from({ length: 3 }, (_, i) => <Skeleton key={i} className="h-24 w-full" />)}</div>
        <div className="space-y-3">{Array.from({ length: 5 }, (_, i) => <Skeleton key={i} className="h-8 w-full" />)}</div>
      </div>
    </div>
  )
}

export function TicketPage({ ticketId }: { ticketId: string }) {
  const { workspace } = useWorkspace()
  const overview = useTicketOverview(workspace.id, ticketId)
  const changeStatus = useChangeStatus(workspace.id, ticketId)
  const update = useUpdateTicket(workspace.id, ticketId)
  const [editing, setEditing] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const assign = useAssignTicket(workspace.id, ticketId)
  const [drafting, setDrafting] = useState(false)
  const members = useMembers(workspace.id)
  useDocumentTitle(overview.data ? `#${overview.data.ticket.number} ${overview.data.ticket.subject} · ResolveAI` : 'Ticket · ResolveAI')

  if (overview.isPending) return <PageSkeleton />
  if (overview.error) {
    const notFound = overview.error instanceof ApiError && overview.error.status === 404
    return (
      <div className="space-y-4">
        <Button variant="ghost" size="sm" icon={<ArrowLeft />} nativeButton={false} render={<Link to={`/app/${workspace.id}/tickets` as never} />}>Tickets</Button>
        <ErrorPanel error={overview.error} onRetry={notFound ? undefined : () => void overview.refetch()} title={notFound ? 'Ticket not found' : 'This ticket could not be loaded'} />
      </div>
    )
  }

  const { ticket, viewer, messages, events, meta, email } = overview.data
  const isOwner = viewer.role === 'owner'
  const canManage = viewer.permissions.includes('tickets.manage')
  const closed = ticket.status === 'closed'
  // Server rules: on a closed ticket only the owner changes anything; nobody replies to the customer.
  const lock = !canManage ? 'You do not have permission to change tickets.' : closed && !isOwner ? REOPEN_ONLY_OWNER : null

  const canAssign = viewer.permissions.includes('tickets.assign')
  const assignLock = !canAssign ? 'You do not have permission to assign tickets.' : closed && !isOwner ? REOPEN_ONLY_OWNER : null
  const assigneeOptions: SelectOption[] = [
    { value: UNASSIGNED, label: 'Unassigned', icon: UserCircleDashed },
    ...(members.data ?? []).map((m) => ({ value: m.user_id, label: m.display_name, icon: User })),
    // A departed member can still be the assignee of a resolved or closed ticket.
    ...(ticket.assignee && !members.data?.some((m) => m.user_id === ticket.assignee?.id) ? [{ value: ticket.assignee.id, label: ticket.assignee.display_name, icon: User }] : []),
  ]
  const onAssign = (value: string) =>
    assign.mutate(value === UNASSIGNED ? null : value, { onSuccess: () => toast.success(value === UNASSIGNED ? 'Ticket unassigned.' : 'Ticket assigned.'), onError: (e) => toast.error(errorMessage(e)) })
  const onStatus = (status: string) =>
    changeStatus.mutate(status as TicketStatusValue, { onSuccess: () => toast.success('Status updated.'), onError: (e) => toast.error(errorMessage(e)) })
  const onField = (changes: { priority?: TicketPriorityValue; category?: TicketCategoryValue }) =>
    update.mutate(changes, { onSuccess: () => toast.success('Ticket updated.'), onError: (e) => toast.error(errorMessage(e)) })

  return (
    <div className="space-y-5">
      <div className="space-y-3">
        <Button variant="ghost" size="sm" icon={<ArrowLeft />} nativeButton={false} render={<Link to={`/app/${workspace.id}/tickets` as never} />}>Tickets</Button>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 space-y-1">
            <h1 className="font-display text-2xl font-semibold tracking-tight text-balance [overflow-wrap:anywhere]"><span className="tabular-nums text-muted-foreground">#{ticket.number}</span> {ticket.subject}</h1>
            <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
              <TicketStatusBadge status={ticket.status} />
              {ticket.waiting_for_reply && <SoftBadge tone="warning" icon={Clock}>Waiting for reply</SoftBadge>}
              <span>{ticket.customer_name ? `${ticket.customer_name} · ` : ''}{ticket.customer_email}</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
          <Button variant="outline" icon={<MagicWand />} onClick={() => setDrafting(true)}>Draft reply</Button>
          <DropdownMenu>
            <DropdownMenuTrigger render={<Button variant="outline" size="icon" label="Ticket actions" />}><DotsThreeVertical weight="bold" /></DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-max min-w-48">
              <DropdownMenuItem disabled={lock !== null} onClick={() => setEditing(true)}>
                <PencilSimple />
                <span className="flex flex-col"><span>Edit details</span>{lock && <span className="max-w-56 text-xs text-muted-foreground">{lock}</span>}</span>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setShowHistory(true)}><ClockCounterClockwise />History</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <Conversation workspaceId={workspace.id} ticketId={ticket.id} messages={messages} total={meta.messages_total} returned={meta.messages_returned} rules={{ canManage, closed, email }} />
        <aside aria-label="Ticket details" className="space-y-6">
          <section aria-labelledby="props" className="space-y-1">
            <h2 id="props" className="sr-only">Properties</h2>
            <PropertyRow label="Status" htmlFor="p-status">
              <Restricted reason={lock}>
                <OptionSelect id="p-status" value={ticket.status} onValueChange={onStatus} options={STATUS_OPTIONS.filter((o) => o.value !== 'none')} />
              </Restricted>
            </PropertyRow>
            <PropertyRow label="Priority" htmlFor="p-priority">
              <Restricted reason={lock}>
                <OptionSelect id="p-priority" value={ticket.priority} onValueChange={(v) => onField({ priority: v as TicketPriorityValue })} options={REAL_PRIORITIES} />
              </Restricted>
            </PropertyRow>
            <PropertyRow label="Category" htmlFor="p-category">
              <Restricted reason={lock}>
                <OptionSelect id="p-category" value={ticket.category} onValueChange={(v) => onField({ category: v as TicketCategoryValue })} options={CATEGORY_OPTIONS} />
              </Restricted>
            </PropertyRow>
            <PropertyRow label="Assignee" htmlFor="p-assignee">
              <Restricted reason={assignLock}>
                <OptionSelect id="p-assignee" value={ticket.assignee?.id ?? UNASSIGNED} onValueChange={onAssign} options={assigneeOptions} />
              </Restricted>
            </PropertyRow>
            <PropertyRow label="Source"><ChannelLabel channel={ticket.created_via} /></PropertyRow>
            <PropertyRow label="Created"><span className="text-sm">{formatDateTime(ticket.created_at)}</span></PropertyRow>
            <PropertyRow label="Last activity"><span className="text-sm">{formatDateTime(ticket.last_activity_at)}</span></PropertyRow>
            {ticket.resolved_at && <PropertyRow label="Resolved"><span className="text-sm">{formatDateTime(ticket.resolved_at)}</span></PropertyRow>}
          </section>
          <SummarySection workspaceId={workspace.id} ticketId={ticket.id} />
        </aside>
      </div>

      {drafting && <DraftReplyDialog workspaceId={workspace.id} ticketId={ticket.id} open onOpenChange={setDrafting} />}
      {showHistory && <HistoryDialog workspaceId={workspace.id} ticketId={ticket.id} number={ticket.number} events={events} total={meta.events_total} returned={meta.events_returned} open onOpenChange={setShowHistory} />}
      {editing && <EditTicketDialog key={ticket.updated_at} workspaceId={workspace.id} ticket={ticket} open onOpenChange={setEditing} />}
    </div>
  )
}
