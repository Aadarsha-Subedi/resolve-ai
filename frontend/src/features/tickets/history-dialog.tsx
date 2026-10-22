import { formatDistanceToNowStrict } from 'date-fns'

import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { ErrorPanel } from '@/features/app/page-states'
import { useOlder } from '@/features/tickets/api'
import { describeEvent } from '@/features/tickets/ticket-events'
import { ArrowUp, Clock, X } from '@/icons'
import { formatDateTime } from '@/lib/format'
import type { TicketEvent } from '@/lib/types'

/** The ticket's history, newest first, in a dialog. Mounted only while open, so older entries load on demand. */
export function HistoryDialog({ workspaceId, ticketId, number, events, total, returned, open, onOpenChange }: { workspaceId: string; ticketId: string; number: number; events: TicketEvent[]; total: number; returned: number; open: boolean; onOpenChange: (open: boolean) => void }) {
  const older = useOlder<TicketEvent>(`/workspaces/${workspaceId}/tickets/${ticketId}/events/`, total, returned)
  const all = [...older.older, ...events].reverse()
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>History of ticket #{number}</DialogTitle>
          <DialogDescription>Every change, newest first. Message text is not repeated here.</DialogDescription>
        </DialogHeader>
        <div className="max-h-[60vh] space-y-3 overflow-y-auto pr-1">
          <ol className="space-y-2.5" aria-label="History">
            {all.map((event) => (
              <li key={event.id} className="flex gap-2 text-sm">
                <Clock className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden />
                <span>
                  <span className="text-foreground">{describeEvent(event)}</span>
                  <span className="block text-xs text-muted-foreground" title={formatDateTime(event.created_at)}>{formatDistanceToNowStrict(new Date(event.created_at), { addSuffix: true })}</span>
                </span>
              </li>
            ))}
          </ol>
          {older.remaining > 0 && <Button variant="outline" size="sm" icon={<ArrowUp />} loading={older.loading} onClick={() => void older.load()}>Load older history</Button>}
          {older.error != null && <ErrorPanel error={older.error} onRetry={() => void older.load()} />}
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" icon={<X />} onClick={() => onOpenChange(false)}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
