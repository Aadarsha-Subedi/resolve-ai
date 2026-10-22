import { useNavigate } from '@tanstack/react-router'
import { toast } from 'sonner'

import { PageHeader } from '@/components/patterns/page-header'
import { Button } from '@/components/ui/button'
import { EmptyState, ErrorPanel, LinesSkeleton } from '@/features/app/page-states'
import { useAnswerInvitation, useMyInvitations } from '@/features/workspaces/api'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { Check, EnvelopeSimple, X } from '@/icons'
import { errorMessage } from '@/lib/api'
import { formatDateTime } from '@/lib/format'

export function InvitationsPage() {
  useDocumentTitle('Invitations · ResolveAI')
  const navigate = useNavigate()
  const invitations = useMyInvitations()
  const answer = useAnswerInvitation()

  const respond = (id: string, accept: boolean) =>
    answer.mutate(
      { id, accept },
      {
        onSuccess: ({ workspace }) => {
          if (workspace) {
            toast.success(`You joined ${workspace.name}.`)
            void navigate({ to: `/app/${workspace.id}` as never })
          } else toast.success('Invitation declined.')
        },
        onError: (error) => toast.error(errorMessage(error)),
      },
    )

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <PageHeader title="Invitations" description="Workspaces that invited your Google account." />
      {invitations.isPending ? (
        <LinesSkeleton rows={3} />
      ) : invitations.error ? (
        <ErrorPanel error={invitations.error} onRetry={() => void invitations.refetch()} />
      ) : invitations.data.length === 0 ? (
        <EmptyState icon={EnvelopeSimple} title="No open invitations">When an owner invites your Google account, it appears here.</EmptyState>
      ) : (
        <ul className="divide-y rounded-xl border">
          {invitations.data.map((invitation) => (
            <li key={invitation.id} className="flex flex-wrap items-center gap-3 p-4">
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{invitation.workspace.name}</p>
                {invitation.expires_at && <p className="text-xs text-muted-foreground">Expires {formatDateTime(invitation.expires_at)}</p>}
              </div>
              <Button variant="outline" size="sm" icon={<X />} disabled={answer.isPending} onClick={() => respond(invitation.id, false)}>Decline</Button>
              <Button size="sm" icon={<Check />} loading={answer.isPending && answer.variables?.id === invitation.id} onClick={() => respond(invitation.id, true)}>Accept</Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
