import { useNavigate } from '@tanstack/react-router'
import { useState } from 'react'
import { toast } from 'sonner'

import { ConfirmDialog } from '@/components/patterns/confirm-dialog'
import { PageHeader } from '@/components/patterns/page-header'
import { Restricted } from '@/components/patterns/restricted'
import { SoftBadge } from '@/components/patterns/ticket-meta'
import { UserAvatar } from '@/components/patterns/user-avatar'
import { Button } from '@/components/ui/button'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ErrorPanel, LinesSkeleton } from '@/features/app/page-states'
import { OWNER_ONLY, useWorkspace } from '@/features/app/workspace-context'
import { InvitationsPanel } from '@/features/workspaces/invitations-panel'
import { JoinLinkPanel } from '@/features/workspaces/join-link-panel'
import { useLeaveWorkspace, useMembers, useRemoveMember, useTransferOwnership, type Member } from '@/features/workspaces/api'
import { useQuery } from '@tanstack/react-query'
import { currentUserQuery } from '@/features/auth/api'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { Crown, DotsThreeVertical, EnvelopeSimple, LinkSimple, SignOut, UserMinus, UsersThree } from '@/icons'
import { errorMessage } from '@/lib/api'
import { formatPlainDate } from '@/lib/format'

type Pending = { kind: 'remove' | 'transfer'; member: Member } | null

function MembersPanel() {
  const { workspace, isOwner } = useWorkspace()
  const me = useQuery(currentUserQuery)
  const members = useMembers(workspace.id)
  const remove = useRemoveMember(workspace.id)
  const transfer = useTransferOwnership(workspace.id)
  const [pending, setPending] = useState<Pending>(null)

  if (members.isPending) return <LinesSkeleton rows={4} />
  if (members.error) return <ErrorPanel error={members.error} onRetry={() => void members.refetch()} />

  const done = (message: string) => ({ onSuccess: () => toast.success(message), onError: (e: unknown) => toast.error(errorMessage(e)) })
  const confirm = () => {
    if (!pending) return
    if (pending.kind === 'remove') remove.mutate(pending.member.user_id, done(`${pending.member.display_name} was removed.`))
    else transfer.mutate(pending.member.user_id, done(`${pending.member.display_name} is now the owner.`))
  }

  return (
    <div className="space-y-4">
      <ul className="divide-y rounded-xl border">
        {members.data.map((member) => {
          const self = member.user_id === me.data?.id
          return (
            <li key={member.user_id} className="flex flex-wrap items-center gap-3 p-3">
              <UserAvatar name={member.display_name} src={member.avatar_url} />
              <div className="min-w-0 flex-1">
                <p className="flex items-center gap-2 truncate text-sm font-medium">{member.display_name}{self && <span className="text-xs font-normal text-muted-foreground">(you)</span>}</p>
                <p className="truncate text-xs text-muted-foreground">{member.email} · joined {formatPlainDate(member.joined_at.slice(0, 10))}</p>
              </div>
              {member.role === 'owner' ? <SoftBadge tone="info" icon={Crown}>Owner</SoftBadge> : <SoftBadge>Member</SoftBadge>}
              {member.role !== 'owner' && (
                <div className="flex gap-2">
                  <Restricted reason={!isOwner && OWNER_ONLY}>
                    <Button variant="outline" size="sm" icon={<Crown />} onClick={() => setPending({ kind: 'transfer', member })}>Make owner</Button>
                  </Restricted>
                  <Restricted reason={!isOwner && OWNER_ONLY}>
                    <Button variant="destructive" size="sm" icon={<UserMinus />} onClick={() => setPending({ kind: 'remove', member })}>Remove</Button>
                  </Restricted>
                </div>
              )}
            </li>
          )
        })}
      </ul>

      <ConfirmDialog
        open={pending !== null}
        onOpenChange={(open) => !open && setPending(null)}
        title={pending?.kind === 'remove' ? 'Remove this member?' : 'Transfer ownership?'}
        description={
          pending?.kind === 'remove'
            ? `${pending.member.display_name} loses access to ${workspace.name} straight away.`
            : pending?.kind === 'transfer'
              ? `${pending.member.display_name} becomes the only owner and you become a member. Only they can undo it.`
              : ''
        }
        confirmLabel={pending?.kind === 'remove' ? 'Remove member' : 'Transfer ownership'}
        confirmIcon={pending?.kind === 'remove' ? <UserMinus /> : <Crown />}
        destructive
        onConfirm={confirm}
      />
    </div>
  )
}

/** The page's three-dots menu. Leaving keeps its confirm dialog; the owner sees the item disabled with the reason. */
function PageMenu() {
  const { workspace, isOwner } = useWorkspace()
  const navigate = useNavigate()
  const leave = useLeaveWorkspace(workspace.id)
  const [confirming, setConfirming] = useState(false)
  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger render={<Button variant="outline" size="icon" label="More actions" />}><DotsThreeVertical weight="bold" /></DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-max min-w-52">
          <DropdownMenuItem disabled={isOwner} onClick={() => setConfirming(true)}>
            <SignOut />
            <span className="flex flex-col"><span>Leave workspace</span>{isOwner && <span className="text-xs text-muted-foreground">Transfer ownership first</span>}</span>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <ConfirmDialog
        open={confirming}
        onOpenChange={setConfirming}
        title="Leave this workspace?"
        description={`You lose access to ${workspace.name}. An owner or an invitation is needed to come back.`}
        confirmLabel="Leave workspace"
        confirmIcon={<SignOut />}
        destructive
        onConfirm={() => leave.mutate(undefined, { onSuccess: () => { toast.success(`You left ${workspace.name}.`); void navigate({ to: '/app' }) }, onError: (e) => toast.error(errorMessage(e)) })}
      />
    </>
  )
}

export function MembersPage() {
  useDocumentTitle('Members · ResolveAI')
  const { isOwner } = useWorkspace()
  const [tab, setTab] = useState<'members' | 'link' | 'invites'>('members')
  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <PageHeader title="Members" description="Who can work in this workspace, and how people join." actions={<PageMenu />} />
      <Tabs value={tab} onValueChange={(v) => setTab(v as typeof tab)}>
        <TabsList>
          <TabsTrigger value="members"><UsersThree />Members</TabsTrigger>
          <Restricted reason={!isOwner && OWNER_ONLY}><TabsTrigger value="link"><LinkSimple />Join link</TabsTrigger></Restricted>
          <Restricted reason={!isOwner && OWNER_ONLY}><TabsTrigger value="invites"><EnvelopeSimple />Invitations</TabsTrigger></Restricted>
        </TabsList>
      </Tabs>
      {tab === 'members' && <MembersPanel />}
      {tab === 'link' && <JoinLinkPanel />}
      {tab === 'invites' && <InvitationsPanel />}
    </div>
  )
}
