import { formatDistanceToNowStrict } from 'date-fns'

import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { useConversations, type Conversation } from '@/features/ai/context-api'
import { ErrorPanel, LinesSkeleton } from '@/features/app/page-states'
import { Trash, X } from '@/icons'
import { cn } from '@/lib/utils'

/** Your saved chats in this workspace, newest first. Picking one loads it. Mounted only while open. */
export function AskHistoryDialog({ workspaceId, activeId, open, onOpenChange, onPick, onDelete }: {
  workspaceId: string
  activeId: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onPick: (id: string) => void
  onDelete: (conversation: Conversation) => void
}) {
  const list = useConversations(workspaceId)
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Chat history</DialogTitle>
          <DialogDescription>Only you can see your chats in this workspace.</DialogDescription>
        </DialogHeader>
        <div className="max-h-[60vh] overflow-y-auto pr-1">
          {list.isPending ? <LinesSkeleton rows={4} />
            : list.error ? <ErrorPanel error={list.error} onRetry={() => void list.refetch()} title="History could not be loaded" />
            : list.data.items.length === 0 ? <p className="py-6 text-center text-sm text-muted-foreground">No chats yet. Ask a question to start one.</p>
            : (
              <ul className="space-y-0.5" aria-label="Chats">
                {list.data.items.map((c) => (
                  <li key={c.id} className={cn('group flex items-center gap-1 rounded-md', c.id === activeId && 'bg-muted')}>
                    <button type="button" aria-current={c.id === activeId} onClick={() => onPick(c.id)} className="min-w-0 flex-1 rounded-md px-2 py-2 text-left outline-none hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring/50">
                      <span className="block truncate text-sm font-medium">{c.title}</span>
                      <span className="block text-xs text-muted-foreground">{c.turn_count ?? 0} {c.turn_count === 1 ? 'question' : 'questions'} · {formatDistanceToNowStrict(new Date(c.updated_at), { addSuffix: true })}</span>
                    </button>
                    <Button variant="ghost" size="icon-sm" label={`Delete chat ${c.title}`} onClick={() => onDelete(c)} className="opacity-0 group-focus-within:opacity-100 group-hover:opacity-100 pointer-coarse:opacity-100"><Trash /></Button>
                  </li>
                ))}
              </ul>
            )}
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" icon={<X />} onClick={() => onOpenChange(false)}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
