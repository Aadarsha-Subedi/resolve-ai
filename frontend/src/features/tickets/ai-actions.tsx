import { useState, type FormEvent } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Field, FieldError, FieldLabel } from '@/components/ui/field'
import { Textarea } from '@/components/ui/textarea'
import { ErrorPanel, LinesSkeleton } from '@/features/app/page-states'
import { DRAFT_INTENT_MAX, useDraftReply, useSummarizeTicket } from '@/features/tickets/ai-api'
import { Copy, MagicWand, Sparkle } from '@/icons'
import { errorMessage } from '@/lib/api'

/** On-demand summary of the public conversation. Internal notes are never sent to the model. */
export function SummarySection({ workspaceId, ticketId }: { workspaceId: string; ticketId: string }) {
  const summarize = useSummarizeTicket(workspaceId, ticketId)
  return (
    <section aria-labelledby="ai-summary" className="space-y-2">
      <h2 id="ai-summary" className="text-sm font-semibold">AI summary</h2>
      <div aria-live="polite" aria-busy={summarize.isPending}>
        {summarize.isPending ? <LinesSkeleton rows={3} />
          : summarize.error ? <ErrorPanel error={summarize.error} title="Summary failed" />
          : summarize.data ? <p className="text-sm leading-relaxed whitespace-pre-wrap [overflow-wrap:anywhere]">{summarize.data}</p>
          : <p className="text-sm text-muted-foreground">Summarise the customer conversation. Internal notes are not shared with the AI.</p>}
      </div>
      <Button variant="outline" size="sm" icon={<Sparkle weight="fill" />} loading={summarize.isPending} onClick={() => summarize.mutate()}>{summarize.data ? 'Summarise again' : 'Summarise ticket'}</Button>
    </section>
  )
}

export function DraftReplyDialog({ workspaceId, ticketId, open, onOpenChange }: { workspaceId: string; ticketId: string; open: boolean; onOpenChange: (open: boolean) => void }) {
  const draft = useDraftReply(workspaceId, ticketId)
  const [intent, setIntent] = useState('')
  const trimmed = intent.trim()

  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (!trimmed || draft.isPending) return
    draft.mutate(trimmed, { onError: (e) => toast.error(errorMessage(e)) })
  }
  const copy = async () => {
    if (!draft.data) return
    try {
      await navigator.clipboard.writeText(draft.data.draft)
      toast.success('Draft copied.')
    } catch {
      toast.error('Could not copy. Select the text and copy it instead.')
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Draft a reply</DialogTitle>
          <DialogDescription>Uses the customer conversation (not internal notes) and matching knowledge base articles. Review it before you send.</DialogDescription>
        </DialogHeader>
        <form id="draft-reply-form" onSubmit={submit} className="space-y-3">
          <Field>
            <FieldLabel htmlFor="dr-intent">What should the reply do?</FieldLabel>
            <Textarea id="dr-intent" value={intent} onChange={(e) => setIntent(e.target.value)} rows={3} maxLength={DRAFT_INTENT_MAX} required placeholder="For example: apologise for the delay and explain the refund steps." />
            <div className="flex justify-between text-xs text-muted-foreground">
              <FieldError>{draft.error ? errorMessage(draft.error) : null}</FieldError>
              <span className="ml-auto tabular-nums" aria-live="polite">{intent.length}/{DRAFT_INTENT_MAX}</span>
            </div>
          </Field>
        </form>
        {draft.data && (
          <div className="space-y-3">
            <Textarea aria-label="Draft reply" readOnly rows={10} value={draft.data.draft} />
            {draft.data.sources.length > 0 && (
              <div className="space-y-1">
                <p className="text-xs font-medium text-muted-foreground">Sources</p>
                <ol className="space-y-0.5 text-xs text-muted-foreground">
                  {draft.data.sources.map((s, i) => <li key={`${s.article_id}-${i}`} className="[overflow-wrap:anywhere]">[{i + 1}] {s.title}{s.section ? ` · ${s.section}` : ''}</li>)}
                </ol>
              </div>
            )}
          </div>
        )}
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Close</Button>
          <Button type="submit" form="draft-reply-form" variant="outline" icon={<MagicWand />} loading={draft.isPending} disabled={!trimmed}>{draft.data ? 'Draft again' : 'Draft reply'}</Button>
          <Button type="button" icon={<Copy />} disabled={!draft.data} onClick={() => void copy()}>Copy draft</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
