import { formatDistanceToNowStrict } from 'date-fns'
import { useState } from 'react'
import { toast } from 'sonner'

import { PageHeader } from '@/components/patterns/page-header'
import { SoftBadge, type Tone } from '@/components/patterns/ticket-meta'
import { Button } from '@/components/ui/button'
import { EmptyState, ErrorPanel, LinesSkeleton } from '@/features/app/page-states'
import { AttachDialog } from '@/features/email/attach-dialog'
import { useDismissReview, useGmailStatus, useReviewItems, useSyncMail, type ReviewItem } from '@/features/email/api'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { ArrowsClockwise, EnvelopeOpen, GoogleLogo, Link as LinkIcon, X } from '@/icons'
import { errorMessage } from '@/lib/api'
import { formatDateTime } from '@/lib/format'
import type { GmailStatusValue } from '@/lib/types'

const STATUS: Record<GmailStatusValue, { label: string; tone: Tone; help: string }> = {
  connected: { label: 'Connected', tone: 'success', help: 'Replies you send go out from your Gmail, and customer replies arrive here.' },
  not_connected: { label: 'Not connected', tone: 'neutral', help: 'Sign in again and allow Gmail access so ResolveAI can send and read ticket mail.' },
  reauth_required: { label: 'Sign in again', tone: 'warning', help: 'Google stopped accepting the saved permission. Sign in again to restore it.' },
  disconnected: { label: 'Disconnected', tone: 'neutral', help: 'Gmail was disconnected. Sign in again to reconnect.' },
}

export function EmailPage() {
  useDocumentTitle('Email · ResolveAI')
  const status = useGmailStatus()
  const review = useReviewItems()
  const sync = useSyncMail()
  const dismiss = useDismissReview()
  const [attaching, setAttaching] = useState<ReviewItem | null>(null)

  const connected = status.data?.status === 'connected'
  const runSync = () =>
    sync.mutate(undefined, {
      onSuccess: (r) => toast.success(`Checked your latest ${r.limit} emails: ${r.matched} added to tickets, ${r.needs_review} to review.`),
      onError: (e) => toast.error(errorMessage(e)),
    })

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <PageHeader title="Email" description="Your Gmail connection and mail that could not be matched to a ticket." />

      <section aria-labelledby="gmail" className="space-y-3">
        <h2 id="gmail" className="text-lg font-semibold">Gmail</h2>
        {status.isPending ? (
          <LinesSkeleton rows={2} />
        ) : status.error ? (
          <ErrorPanel error={status.error} onRetry={() => void status.refetch()} />
        ) : (
          <div className="space-y-3 rounded-xl border p-4">
            <div className="flex flex-wrap items-center gap-3">
              <SoftBadge tone={STATUS[status.data.status].tone}>{STATUS[status.data.status].label}</SoftBadge>
              {status.data.mailbox_email && <span className="text-sm font-medium">{status.data.mailbox_email}</span>}
            </div>
            <p className="max-w-prose text-sm text-muted-foreground">{STATUS[status.data.status].help}</p>
            {connected && (
              <p className="text-xs text-muted-foreground">
                {status.data.last_sync_at ? `Last synced ${formatDateTime(status.data.last_sync_at)}. ` : 'Not synced yet. '}
                {status.data.push_active ? 'New mail arrives automatically.' : 'Automatic delivery is off; use Sync latest mails.'}
              </p>
            )}
            <div className="flex flex-wrap gap-2">
              {connected && <Button icon={<ArrowsClockwise />} loading={sync.isPending} onClick={runSync}>Sync latest mails</Button>}
              {status.data.reconnect_path && <Button variant={connected ? 'outline' : 'default'} icon={<GoogleLogo weight="bold" />} nativeButton={false} render={<a href={status.data.reconnect_path} />}>Reconnect with Google</Button>}
            </div>
          </div>
        )}
      </section>

      <section aria-labelledby="review" className="space-y-3">
        <h2 id="review" className="text-lg font-semibold">Needs review</h2>
        <p className="max-w-prose text-sm text-muted-foreground">Mail from known customers that did not match a ticket by its email headers. Add it to the right ticket or dismiss it.</p>
        {review.isPending ? (
          <LinesSkeleton rows={3} />
        ) : review.error ? (
          <ErrorPanel error={review.error} onRetry={() => void review.refetch()} />
        ) : review.data.length === 0 ? (
          <EmptyState icon={EnvelopeOpen} title="Nothing to review">Unmatched customer mail shows up here after a sync.</EmptyState>
        ) : (
          <ul className="divide-y rounded-xl border">
            {review.data.map((item) => (
              <li key={item.id} className="space-y-2 p-3">
                <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                  <p className="min-w-0 flex-1 truncate text-sm font-medium">{item.subject || '(no subject)'}</p>
                  <time className="text-xs text-muted-foreground" dateTime={item.received_at}>{formatDistanceToNowStrict(new Date(item.received_at), { addSuffix: true })}</time>
                </div>
                <p className="text-xs text-muted-foreground">{item.sender_name ? `${item.sender_name} · ` : ''}{item.sender_email}</p>
                {item.snippet && <p className="line-clamp-2 text-sm text-muted-foreground">{item.snippet}</p>}
                <div className="flex gap-2">
                  <Button size="sm" icon={<LinkIcon />} onClick={() => setAttaching(item)}>Add to ticket</Button>
                  <Button size="sm" variant="outline" icon={<X />} loading={dismiss.isPending && dismiss.variables === item.id} onClick={() => dismiss.mutate(item.id, { onError: (e) => toast.error(errorMessage(e)) })}>Dismiss</Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
      {attaching && <AttachDialog key={attaching.id} item={attaching} onOpenChange={(open) => !open && setAttaching(null)} />}
    </div>
  )
}
