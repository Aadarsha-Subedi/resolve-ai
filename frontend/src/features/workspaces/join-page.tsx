import { Link, useNavigate } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { toast } from 'sonner'

import { Logo } from '@/components/patterns/logo'
import { Button } from '@/components/ui/button'
import { currentUserQuery } from '@/features/auth/api'
import { GoogleButton } from '@/features/marketing/google-button'
import { useRedeemJoinLink } from '@/features/workspaces/api'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { Skeleton } from '@/components/ui/skeleton'
import { errorMessage } from '@/lib/api'

/** Opened from a workspace's join link (/join/{token}). Joining is the visitor's click, never automatic. */
export function JoinPage({ token }: { token: string }) {
  useDocumentTitle('Join a workspace · ResolveAI')
  const navigate = useNavigate()
  const user = useQuery(currentUserQuery)
  const redeem = useRedeemJoinLink()

  const join = () =>
    redeem.mutate(token, {
      onSuccess: ({ workspace, joined }) => {
        toast.success(joined ? `You joined ${workspace.name}.` : `You are already in ${workspace.name}.`)
        void navigate({ to: `/app/${workspace.id}` as never })
      },
    })

  return (
    <main className="grid min-h-svh place-items-center px-6">
      <div className="w-full max-w-sm space-y-6">
        <Link to="/" aria-label="ResolveAI home" className="block w-fit"><Logo /></Link>
        <div className="space-y-2">
          <h1 className="font-display text-2xl font-semibold tracking-tight">Join a workspace</h1>
          <p className="text-sm text-muted-foreground">You were sent a join link. Joining makes you a member who can work its tickets and knowledge base.</p>
        </div>
        {redeem.error && <p role="alert" className="text-sm text-destructive">{errorMessage(redeem.error)} Ask the owner for a new link.</p>}
        {user.isPending ? (
          <Skeleton className="h-9 w-40" />
        ) : user.data ? (
          <Button loading={redeem.isPending} onClick={join}>Join workspace</Button>
        ) : (
          <GoogleButton next={`/join/${token}`}>Sign in with Google to join</GoogleButton>
        )}
      </div>
    </main>
  )
}
