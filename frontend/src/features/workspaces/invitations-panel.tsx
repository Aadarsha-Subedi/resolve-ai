import { useState, type FormEvent } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Field, FieldDescription, FieldError, FieldLabel } from '@/components/ui/field'
import { Textarea } from '@/components/ui/textarea'
import { EmptyState, ErrorPanel, LinesSkeleton } from '@/features/app/page-states'
import { useWorkspace } from '@/features/app/workspace-context'
import { useCreateInvitations, useRevokeInvitation, useWorkspaceInvitations, type InvitationOutcome } from '@/features/workspaces/api'
import { EnvelopeSimple, PaperPlaneTilt, UserPlus, X } from '@/icons'
import { errorMessage, fieldError } from '@/lib/api'
import { formatDateTime } from '@/lib/format'

const OUTCOME: Record<string, string> = {
  invited: 'Invited',
  created: 'Invited',
  already_invited: 'Already invited',
  already_member: 'Already a member',
}

function InviteDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const { workspace } = useWorkspace()
  const create = useCreateInvitations(workspace.id)
  const [text, setText] = useState('')
  const [results, setResults] = useState<InvitationOutcome[]>([])

  const submit = (event: FormEvent) => {
    event.preventDefault()
    const emails = [...new Set(text.split(/[\s,;]+/).map((e) => e.trim()).filter(Boolean))]
    create.mutate(emails, {
      onSuccess: (items) => {
        setResults(items)
        setText('')
      },
      onError: (e) => {
        if (!fieldError(e, 'emails')) toast.error(errorMessage(e))
      },
    })
  }
  const close = (next: boolean) => {
    onOpenChange(next)
    if (!next) {
      setResults([])
      setText('')
      create.reset()
    }
  }

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Invite Google accounts</DialogTitle>
          <DialogDescription>Each person gets an email from your Gmail with a link to accept. They can also accept from their Invitations page.</DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="space-y-4">
          <Field>
            <FieldLabel htmlFor="invite-emails">Google accounts to invite</FieldLabel>
            <Textarea id="invite-emails" rows={3} value={text} onChange={(e) => setText(e.target.value)} placeholder="ana@gmail.com, ben@gmail.com" aria-invalid={!!create.error && !!fieldError(create.error, 'emails')} />
            <FieldDescription>Up to 20 addresses, separated by commas or new lines.</FieldDescription>
            <FieldError>{fieldError(create.error, 'emails')}</FieldError>
          </Field>
          {results.length > 0 && (
            <ul className="space-y-1 text-sm" aria-label="Invitation results">
              {results.map((r) => <li key={r.email}><span className="font-medium">{r.email}</span> <span className="text-muted-foreground">{OUTCOME[r.outcome] ?? r.outcome.replace(/_/g, ' ')}</span></li>)}
            </ul>
          )}
          <DialogFooter>
            <Button type="button" variant="outline" icon={<X />} onClick={() => close(false)}>{results.length > 0 ? 'Close' : 'Cancel'}</Button>
            <Button type="submit" icon={<PaperPlaneTilt />} loading={create.isPending} disabled={!text.trim()}>Send invitations</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

/** Mounted only while its tab is open: the list of open invitations and an Invite button that opens the form in a dialog. */
export function InvitationsPanel() {
  const { workspace } = useWorkspace()
  const invitations = useWorkspaceInvitations(workspace.id, true)
  const revoke = useRevokeInvitation(workspace.id)
  const [inviting, setInviting] = useState(false)

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-muted-foreground">Invitations wait here until they are accepted, declined or expire.</p>
        <Button icon={<UserPlus />} onClick={() => setInviting(true)}>Invite</Button>
      </div>
      {invitations.isPending ? (
        <LinesSkeleton rows={3} />
      ) : invitations.error ? (
        <ErrorPanel error={invitations.error} onRetry={() => void invitations.refetch()} />
      ) : invitations.data.length === 0 ? (
        <EmptyState icon={EnvelopeSimple} title="No open invitations">Use Invite above to add teammates by their Google account.</EmptyState>
      ) : (
        <ul className="divide-y rounded-xl border">
          {invitations.data.map((invitation) => (
            <li key={invitation.id} className="flex flex-wrap items-center gap-3 p-3">
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{invitation.email}</p>
                <p className="text-xs text-muted-foreground">Expires {formatDateTime(invitation.expires_at)}</p>
              </div>
              <Button variant="outline" size="sm" icon={<X />} loading={revoke.isPending && revoke.variables === invitation.id} onClick={() => revoke.mutate(invitation.id, { onError: (e) => toast.error(errorMessage(e)) })}>Revoke</Button>
            </li>
          ))}
        </ul>
      )}
      <InviteDialog open={inviting} onOpenChange={setInviting} />
    </div>
  )
}
