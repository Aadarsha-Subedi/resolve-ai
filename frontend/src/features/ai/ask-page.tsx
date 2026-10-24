import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { toast } from 'sonner'

import { ConfirmDialog } from '@/components/patterns/confirm-dialog'
import { Button } from '@/components/ui/button'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { Textarea } from '@/components/ui/textarea'
import { useLlmSettings } from '@/features/ai/api'
import { currentUserQuery } from '@/features/auth/api'
import { AskHistoryDialog } from '@/features/ai/ask-history-dialog'
import { AskUsageDialog } from '@/features/ai/ask-usage-dialog'
import { AskModelDialog } from '@/features/ai/ask-model-dialog'
import { AgentAvatar, PendingTurn, TurnView } from '@/features/ai/ask-messages'
import { useAskQuestion, useConversation, useDeleteConversation, type Conversation } from '@/features/ai/context-api'
import { ErrorPanel, LinesSkeleton } from '@/features/app/page-states'
import { useWorkspace } from '@/features/app/workspace-context'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { ChartBar, Cpu, ClockCounterClockwise, DotsThreeVertical, PaperPlaneTilt, Plug, Plus } from '@/icons'
import { errorMessage } from '@/lib/api'

const GREETINGS = ['Hello', 'Good to have you', 'Welcome back', 'Nice to see you']

/** Chat over the knowledge base. Chats are saved per user in this workspace; answers are paraphrased from published articles, with numbered sources. */
export function AskPage({ initialQuestion }: { initialQuestion?: string } = {}) {
  useDocumentTitle('Ask · ResolveAI')
  const { workspace } = useWorkspace()
  const ask = useAskQuestion(workspace.id)
  const settings = useLlmSettings(workspace.id)
  const remove = useDeleteConversation(workspace.id)
  const [activeId, setActiveId] = useState<string | null>(null)
  const chat = useConversation(workspace.id, activeId)
  const user = useQuery(currentUserQuery)
  const firstName = user.data?.display_name?.split(' ')[0]
  const [greeting] = useState(() => GREETINGS[Math.floor(Math.random() * GREETINGS.length)])
  const [text, setText] = useState('')
  const [pending, setPending] = useState<{ question: string; error?: unknown } | null>(null)
  const [historyOpen, setHistoryOpen] = useState(false)
  const [usageOpen, setUsageOpen] = useState(false)
  const [modelOpen, setModelOpen] = useState(false)
  const navigate = useNavigate()
  const [deleting, setDeleting] = useState<Conversation | null>(null)
  const end = useRef<HTMLDivElement>(null)
  const turns = chat.data?.turns ?? []
  const busy = ask.isPending
  const usage = settings.data?.mode === 'resolve_ai' ? settings.data.usage : null
  const exhausted = usage?.remaining === 0

  useEffect(() => {
    end.current?.scrollIntoView?.({ block: 'end' })
  }, [turns.length, pending])

  const send = (question: string) => {
    setPending({ question })
    ask.mutate(
      { query: question, conversation_id: activeId },
      {
        onSuccess: (turn) => {
          setActiveId(turn.conversation_id)
          setPending(null)
        },
        onError: (error) => setPending({ question, error }),
      },
    )
  }
  // A question sent here from a ticket message starts a new chat once.
  const sentInitial = useRef(false)
  useEffect(() => {
    if (!initialQuestion || sentInitial.current) return
    sentInitial.current = true
    send(initialQuestion)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialQuestion])
  const submit = (event?: FormEvent) => {
    event?.preventDefault()
    const question = text.trim()
    if (question.length < 2 || busy || exhausted) return
    setText('')
    send(question)
  }
  const onKey = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key !== 'Enter' || event.shiftKey || event.nativeEvent.isComposing) return
    event.preventDefault()
    submit()
  }
  const open = (id: string | null) => {
    setActiveId(id)
    setPending(null)
    setHistoryOpen(false)
  }

  return (
    <div className="-mb-6 flex min-h-[calc(100dvh-4.5rem)] flex-col gap-6">
      <header className="sticky top-12 z-10 -mx-1 flex items-start justify-center bg-background px-1 pt-1 pb-3">
        <div className="min-w-0 space-y-1 px-12 text-center">
          <h1 className="font-display text-2xl font-semibold tracking-tight text-balance">{`Ask about ${workspace.name}'s knowledge base`}</h1>
          <p className="text-sm text-muted-foreground">Answers use published articles and uploaded files.</p>
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger render={<Button variant="outline" size="icon" label="Chat options" className="absolute top-1 right-1" />}><DotsThreeVertical weight="bold" /></DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-max min-w-44">
            <DropdownMenuItem onClick={() => setHistoryOpen(true)}><ClockCounterClockwise />Chat history</DropdownMenuItem>
            <DropdownMenuItem onClick={() => open(null)}><Plus />New chat</DropdownMenuItem>
            <DropdownMenuItem onClick={() => setModelOpen(true)}><Cpu />Model</DropdownMenuItem>
            <DropdownMenuItem onClick={() => setUsageOpen(true)}><ChartBar />Usage</DropdownMenuItem>
            <DropdownMenuItem onClick={() => void navigate({ to: `/app/${workspace.id}/settings` as never, hash: 'ai' })}><Plug />Connect your own agent</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </header>
      <div className="flex flex-1 flex-col">
        <section aria-label="Chat" className="mx-auto flex w-full max-w-3xl min-w-0 flex-1 flex-col gap-6">
          {activeId && chat.isPending ? <LinesSkeleton rows={4} />
            : activeId && chat.error ? <ErrorPanel error={chat.error} onRetry={() => void chat.refetch()} title="This chat could not be loaded" />
            : turns.length === 0 && !pending ? (
              <div className="flex flex-col items-center gap-3 py-16 text-center">
                <AgentAvatar className="size-12" />
                <h2 className="font-display text-lg font-semibold">{firstName ? `${greeting}, ${firstName}` : greeting}</h2>
              </div>
            ) : (
              <ol className="space-y-6" aria-label="Messages">
                {turns.map((turn) => <TurnView key={turn.turn_id} workspaceId={workspace.id} turn={turn} />)}
                {pending && <PendingTurn question={pending.question} error={pending.error} onRetry={() => send(pending.question)} />}
              </ol>
            )}
          <div ref={end} />
          <form onSubmit={submit} className="sticky bottom-0 mt-auto space-y-2 bg-background pb-4">
            <div className="relative">
              <Textarea aria-label="Your question" placeholder={exhausted ? 'The daily limit is reached' : 'Ask about the knowledge base'} rows={2} maxLength={2000} disabled={exhausted} value={text} onChange={(e) => setText(e.target.value)} onKeyDown={onKey} className="pr-12" />
              <div className="pointer-events-none absolute inset-y-0 right-2 flex items-center">
                <Button type="submit" variant="ghost" size="icon-sm" label="Send question" loading={busy} disabled={text.trim().length < 2 || exhausted} className="pointer-events-auto rounded-full bg-transparent hover:bg-muted disabled:bg-transparent"><PaperPlaneTilt weight="fill" /></Button>
              </div>
            </div>
            {settings.data?.mode === 'resolve_ai' && <p className="text-center text-xs text-muted-foreground">Resolve AI uses a free model, responses may be slower</p>}
            {usage && exhausted && <p className="text-xs text-muted-foreground" aria-live="polite">{`Daily limit reached. Resets ${new Date(usage.resets_at).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })}.`}</p>}
          </form>
        </section>
      </div>
      {historyOpen && (
        <AskHistoryDialog workspaceId={workspace.id} activeId={activeId} open onOpenChange={setHistoryOpen} onPick={open} onDelete={(c) => { setHistoryOpen(false); setDeleting(c) }} />
      )}
      {modelOpen && <AskModelDialog workspaceId={workspace.id} open onOpenChange={setModelOpen} />}
      {usageOpen && <AskUsageDialog workspaceId={workspace.id} open onOpenChange={setUsageOpen} />}
      <ConfirmDialog
        open={!!deleting}
        onOpenChange={(o) => !o && setDeleting(null)}
        title="Delete this chat?"
        description={deleting ? `“${deleting.title}” and its answers are removed for good.` : ''}
        confirmLabel="Delete chat"
        destructive
        onConfirm={() => {
          const target = deleting
          if (!target) return
          remove.mutate(target.id, {
            onSuccess: () => {
              if (target.id === activeId) open(null)
              toast.success('Chat deleted.')
            },
            onError: (e) => toast.error(errorMessage(e)),
          })
        }}
      />
    </div>
  )
}
