import { useState } from 'react'
import { toast } from 'sonner'

import { OptionSelect } from '@/components/patterns/option-select'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { ErrorPanel, LinesSkeleton } from '@/features/app/page-states'
import { useWorkspace } from '@/features/app/workspace-context'
import { useCreateJoinLink, useJoinLink, useRevokeJoinLink, type IssuedJoinLink } from '@/features/workspaces/api'
import { Copy, LinkBreak, LinkSimple, X } from '@/icons'
import { errorMessage } from '@/lib/api'
import { formatDateTime } from '@/lib/format'

const EXPIRY = [
  { value: '1h', label: 'Expires in 1 hour' },
  { value: '1d', label: 'Expires in 1 day' },
  { value: '7d', label: 'Expires in 7 days' },
]

/** Mounted only while its tab is open. The link itself is shown once, right after it is created. */
export function JoinLinkPanel() {
  const { workspace } = useWorkspace()
  const status = useJoinLink(workspace.id, true)
  const create = useCreateJoinLink(workspace.id)
  const revoke = useRevokeJoinLink(workspace.id)
  const [expiry, setExpiry] = useState<'1h' | '1d' | '7d'>('1h')
  const [issued, setIssued] = useState<IssuedJoinLink | null>(null)
  const [showLink, setShowLink] = useState(false)

  if (status.isPending) return <LinesSkeleton rows={2} />
  if (status.error) return <ErrorPanel error={status.error} onRetry={() => void status.refetch()} />

  const active = status.data.active
  return (
    <div className="space-y-4">
      <p className="max-w-prose text-sm text-muted-foreground">Anyone signed in with Google who opens the link joins as a member. {active && status.data.expires_at ? `The current link expires ${formatDateTime(status.data.expires_at)}.` : 'There is no active link.'}</p>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="w-52"><OptionSelect value={expiry} onValueChange={(v) => setExpiry(v as typeof expiry)} options={EXPIRY} /></div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            icon={<LinkSimple />}
            loading={create.isPending}
            onClick={() => create.mutate(expiry, { onSuccess: (link) => { setIssued(link); setShowLink(true) }, onError: (e) => toast.error(errorMessage(e)) })}
          >
            {active ? 'Replace link' : 'Create link'}
          </Button>
          {active && (
            <Button variant="destructive" icon={<LinkBreak />} loading={revoke.isPending} onClick={() => revoke.mutate(undefined, { onSuccess: () => { setIssued(null); toast.success('Join link revoked.') }, onError: (e) => toast.error(errorMessage(e)) })}>Revoke</Button>
          )}
        </div>
      </div>
      <Dialog open={showLink && issued !== null} onOpenChange={setShowLink}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Your join link</DialogTitle>
            <DialogDescription>Copy it now: the link is not shown again. {issued?.expires_at ? `It expires ${formatDateTime(issued.expires_at)}.` : ''}</DialogDescription>
          </DialogHeader>
          <div className="flex gap-2">
            <Input readOnly value={issued?.url ?? ''} aria-label="Join link" onFocus={(e) => e.currentTarget.select()} />
            <Button variant="outline" size="icon" label="Copy link" onClick={() => void navigator.clipboard.writeText(issued?.url ?? '').then(() => toast.success('Link copied.'), () => toast.error('Copy failed. Select the text and copy it.'))}><Copy /></Button>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" icon={<X />} onClick={() => setShowLink(false)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
