import { useState } from 'react'
import { toast } from 'sonner'

import { OptionSelect } from '@/components/patterns/option-select'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { SearchBox } from '@/components/patterns/search-box'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { ErrorPanel, LinesSkeleton } from '@/features/app/page-states'
import { LinkSimple, X } from '@/icons'
import { useAttachReview, type ReviewItem } from '@/features/email/api'
import { useTickets } from '@/features/tickets/api'
import { useWorkspaces } from '@/features/workspaces/api'
import { errorMessage } from '@/lib/api'

/** Tickets are fetched only once a workspace is chosen, and only for this dialog. */
function TicketPicker({ workspaceId, q, value, onChange }: { workspaceId: string; q: string; value: string; onChange: (id: string) => void }) {
  const tickets = useTickets(workspaceId, { q: q || undefined })
  if (tickets.isPending) return <LinesSkeleton rows={3} />
  if (tickets.error) return <ErrorPanel error={tickets.error} onRetry={() => void tickets.refetch()} />
  if (tickets.data.items.length === 0) return <p className="text-sm text-muted-foreground">No tickets found.</p>
  return (
    <RadioGroup value={value} onValueChange={onChange} className="max-h-56 gap-1 overflow-y-auto" aria-label="Tickets">
      {tickets.data.items.map((t) => (
        <label key={t.id} className="flex cursor-pointer items-center gap-3 rounded-lg border p-2 text-sm has-data-checked:border-primary/40 has-data-checked:bg-accent">
          <RadioGroupItem value={t.id} />
          <span className="tabular-nums text-muted-foreground">#{t.number}</span>
          <span className="min-w-0 flex-1 truncate">{t.subject}</span>
        </label>
      ))}
    </RadioGroup>
  )
}

export function AttachDialog({ item, onOpenChange }: { item: ReviewItem | null; onOpenChange: (open: boolean) => void }) {
  const workspaces = useWorkspaces()
  const attach = useAttachReview()
  const [workspaceId, setWorkspaceId] = useState('')
  const [q, setQ] = useState('')
  const [ticketId, setTicketId] = useState('')
  return (
    <Dialog open={item !== null} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add to a ticket</DialogTitle>
          <DialogDescription>{item ? `"${item.subject || '(no subject)'}" from ${item.sender_email} becomes a customer reply on the ticket you choose.` : ''}</DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <OptionSelect value={workspaceId || undefined} placeholder="Choose a workspace" onValueChange={(v) => { setWorkspaceId(v); setTicketId('') }} options={(workspaces.data ?? []).map((w) => ({ value: w.id, label: w.name }))} />
          {workspaceId && (
            <>
              <SearchBox value={q} onCommit={(v) => { setQ(v ?? ''); setTicketId('') }} placeholder="Search tickets" />
              <TicketPicker workspaceId={workspaceId} q={q} value={ticketId} onChange={setTicketId} />
            </>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" icon={<X />} onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button
            icon={<LinkSimple />}
            loading={attach.isPending}
            disabled={!ticketId}
            onClick={() => item && attach.mutate({ id: item.id, workspaceId, ticketId }, { onSuccess: () => { toast.success('Email added to the ticket.'); onOpenChange(false) }, onError: (e) => toast.error(errorMessage(e)) })}
          >
            Add to ticket
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
