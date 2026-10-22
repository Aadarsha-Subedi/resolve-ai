import { formatDistanceToNowStrict } from 'date-fns'
import { useState } from 'react'
import { toast } from 'sonner'

import { Restricted } from '@/components/patterns/restricted'
import { SoftBadge } from '@/components/patterns/ticket-meta'
import { UserAvatar } from '@/components/patterns/user-avatar'
import { Button } from '@/components/ui/button'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import { ErrorPanel } from '@/features/app/page-states'
import { useAddMessage, useOlder, useResendMessage } from '@/features/tickets/api'
import { ArrowClockwise, ArrowUp, Clock, EnvelopeSimple, LockSimple, MagnifyingGlass, PaperPlaneTilt, WarningCircle } from '@/icons'
import { errorMessage } from '@/lib/api'
import { cn } from '@/lib/utils'
import type { GmailConnection, TicketMessage } from '@/lib/types'

function DeliveryBadge({ message }: { message: TicketMessage }) {
  if (message.visibility !== 'public' || message.direction !== 'outbound') return null
  if (message.delivery_status === 'sent') return <SoftBadge tone="success">Sent by email</SoftBadge>
  if (message.delivery_status === 'failed') return <SoftBadge tone="danger" icon={WarningCircle}>Not delivered</SoftBadge>
  return <SoftBadge tone="neutral" icon={Clock}>Sending</SoftBadge>
}

function MessageItem({ message, onResend, resending, onFindContext, finding }: { message: TicketMessage; onResend: () => void; resending: boolean; onFindContext: () => void; finding: boolean }) {
  const internal = message.visibility === 'internal'
  const customer = message.author_type === 'customer'
  const name = message.author?.display_name ?? (customer ? 'Customer' : 'ResolveAI')
  return (
    <li className={cn('rounded-xl border p-3', internal ? 'border-warning/40 bg-warning-soft' : customer ? 'bg-card' : 'bg-surface')}>
      <div className="flex flex-wrap items-center gap-2">
        <UserAvatar name={name} size="sm" />
        <span className="text-sm font-medium">{name}</span>
        {customer && <span className="text-xs text-muted-foreground">Customer</span>}
        {internal && <SoftBadge tone="warning" icon={LockSimple}>Internal note</SoftBadge>}
        <DeliveryBadge message={message} />
        <time className="ml-auto text-xs text-muted-foreground" dateTime={message.created_at} title={new Date(message.created_at).toLocaleString()}>
          {formatDistanceToNowStrict(new Date(message.created_at), { addSuffix: true })}
        </time>
      </div>
      <p className="mt-2 max-w-prose text-sm leading-relaxed whitespace-pre-wrap [overflow-wrap:anywhere]">{message.body}</p>
      {customer && !internal && (
        <Button className="mt-2" variant="ghost" size="sm" icon={<MagnifyingGlass />} loading={finding} onClick={onFindContext}>Find context</Button>
      )}
      {message.delivery_status === 'failed' && message.visibility === 'public' && (
        <Button className="mt-2" variant="outline" size="sm" icon={<ArrowClockwise />} loading={resending} onClick={onResend}>Resend</Button>
      )}
    </li>
  )
}

export type ComposerRules = {
  canManage: boolean
  closed: boolean
  email: GmailConnection
}

function replyBlock(rules: ComposerRules): string | null {
  if (!rules.canManage) return 'You do not have permission to reply.'
  if (rules.closed) return 'This ticket is closed. Ask the owner to reopen it before replying.'
  if (rules.email.status !== 'connected') return 'Connect your Gmail account (Email page) to email customers. Your text is kept.'
  return null
}

export function Conversation({ workspaceId, ticketId, messages, total, returned, rules, onFindContext, findingMessageId }: {
  workspaceId: string
  ticketId: string
  messages: TicketMessage[]
  total: number
  returned: number
  rules: ComposerRules
  onFindContext: (messageId: string) => void
  /** The customer message whose context search is running, if any. */
  findingMessageId: string | null
}) {
  const older = useOlder<TicketMessage>(`/workspaces/${workspaceId}/tickets/${ticketId}/messages/`, total, returned)
  const add = useAddMessage(workspaceId, ticketId)
  const resend = useResendMessage(workspaceId, ticketId)
  const [mode, setMode] = useState<'public' | 'internal'>('public')
  const [text, setText] = useState('')
  const [resendingId, setResendingId] = useState<string | null>(null)

  const block = mode === 'public' ? replyBlock(rules) : rules.canManage ? null : 'You do not have permission to add notes.'
  const send = () =>
    add.mutate(
      { body: text.trim(), visibility: mode },
      {
        onSuccess: () => {
          setText('')
          toast.success(mode === 'public' ? 'Reply queued for sending.' : 'Note added.')
        },
        onError: (e) => toast.error(errorMessage(e)),
      },
    )

  const all = [...older.older, ...messages]
  return (
    <section aria-label="Conversation" className="space-y-4">
      {older.remaining > 0 && (
        <Button variant="outline" size="sm" icon={<ArrowUp />} loading={older.loading} onClick={() => void older.load()}>Load {Math.min(older.remaining, 100)} older {older.remaining === 1 ? 'message' : 'messages'}</Button>
      )}
      {older.error != null && <ErrorPanel error={older.error} onRetry={() => void older.load()} />}
      <ol className="space-y-3">
        {all.map((message) => (
          <MessageItem
            key={message.id}
            message={message}
            resending={resend.isPending && resendingId === message.id}
            finding={findingMessageId === message.id}
            onFindContext={() => onFindContext(message.id)}
            onResend={() => {
              setResendingId(message.id)
              resend.mutate(message.id, { onSuccess: () => toast.success('Reply queued again.'), onError: (e) => toast.error(errorMessage(e)) })
            }}
          />
        ))}
      </ol>

      <div className="space-y-2 rounded-xl bg-muted/60 p-3">
        <Tabs value={mode} onValueChange={(v) => setMode(v as 'public' | 'internal')}>
          <TabsList>
            <TabsTrigger value="public"><EnvelopeSimple />Reply to customer</TabsTrigger>
            <TabsTrigger value="internal"><LockSimple />Internal note</TabsTrigger>
          </TabsList>
        </Tabs>
        <Textarea
          aria-label={mode === 'public' ? 'Reply to the customer' : 'Internal note'}
          placeholder={mode === 'public' ? 'Write a reply. It is emailed from your Gmail.' : 'Only your team sees this.'}
          rows={4}
          maxLength={20000}
          className="border-transparent bg-background/70 dark:bg-background/40"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <div className="flex justify-end">
          <Restricted reason={block}>
            <Button icon={<PaperPlaneTilt />} loading={add.isPending} disabled={!text.trim()} onClick={send}>{mode === 'public' ? 'Send reply' : 'Add note'}</Button>
          </Restricted>
        </div>
      </div>
    </section>
  )
}
