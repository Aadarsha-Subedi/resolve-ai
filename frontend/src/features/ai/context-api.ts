import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useRefreshLlmUsage } from '@/features/ai/api'
import { api, apiList } from '@/lib/api'

export type ContextHit = {
  citation: number
  score: number
  /** Set for a passage of an article, null for a passage of an uploaded file. */
  article: { id: string; title: string } | null
  /** Where the passage comes from. Missing in chats saved before documents were searched: use `article`. */
  source?: { type: 'article' | 'upload'; id: string; title: string; /** PDF page, when known. */ page: number | null }
  section: string
  chunk_id: string
  /** Plain text with ⟦ ⟧ around the matched words. Never HTML. */
  snippet: string
}

export type ContextResult = {
  terms: string[]
  /** The text that was searched: the original first, then the rewrites when rewriting worked. */
  queries: string[]
  rewritten: boolean
  results: ContextHit[]
}

export type AnswerStatus = 'answered' | 'not_covered' | 'unavailable' | 'no_results'

/** The context payload plus an answer paraphrased from it. `answer` is null unless `status` is "answered". */
export type Answer = ContextResult & { answered?: boolean; status: AnswerStatus; answer: string | null; cited: number[]; reason?: string | null }

/** One question and its answer as stored in the chat history. */
export type AskTurn = Answer & { turn_id: string; question: string; created_at: string }
export type NewAskTurn = AskTurn & { conversation_id: string }
export type Conversation = { id: string; title: string; created_at: string; updated_at: string; turn_count?: number | null; turns?: AskTurn[] }

const askKey = (ws: string) => ['ws', ws, 'ask'] as const

export function useConversations(ws: string) {
  return useQuery({
    queryKey: [...askKey(ws), 'list'],
    queryFn: ({ signal }) => apiList<Conversation>(`/workspaces/${ws}/knowledge/ask/conversations/`, { limit: 50 }, signal),
  })
}

export function useConversation(ws: string, id: string | null) {
  return useQuery({
    queryKey: [...askKey(ws), 'detail', id],
    enabled: !!id,
    queryFn: async ({ signal }) => (await api.get<Conversation>(`/workspaces/${ws}/knowledge/ask/conversations/${id}/`, undefined, signal)).data,
  })
}

/** A question typed into the Ask page. The server stores the exchange; the cached chat gets the new turn at once. */
export function useAskQuestion(ws: string) {
  const client = useQueryClient()
  const refreshUsage = useRefreshLlmUsage(ws)
  return useMutation({
    mutationFn: async (body: { query: string; conversation_id?: string | null }) =>
      (await api.post<NewAskTurn>(`/workspaces/${ws}/knowledge/ask/`, { query: body.query, ...(body.conversation_id ? { conversation_id: body.conversation_id } : {}) })).data,
    onSuccess: ({ conversation_id, ...turn }) => {
      const now = turn.created_at
      client.setQueryData<Conversation>([...askKey(ws), 'detail', conversation_id], (old) =>
        old ? { ...old, updated_at: now, turns: [...(old.turns ?? []), turn] } : { id: conversation_id, title: turn.question.slice(0, 80), created_at: now, updated_at: now, turns: [turn] },
      )
      void client.invalidateQueries({ queryKey: [...askKey(ws), 'list'] })
    },
    onSettled: refreshUsage,
  })
}

export function useDeleteConversation(ws: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => (await api.delete(`/workspaces/${ws}/knowledge/ask/conversations/${id}/`)).message,
    onSuccess: (_message, id) => {
      client.removeQueries({ queryKey: [...askKey(ws), 'detail', id] })
      void client.invalidateQueries({ queryKey: [...askKey(ws), 'list'] })
    },
  })
}

/** The source of a hit, whether it came from the API with `source` or from an older saved chat with only `article`. */
export function hitSource(hit: ContextHit): { type: 'article' | 'upload'; id: string; title: string; page: number | null } {
  return hit.source ?? { type: 'article', id: hit.article?.id ?? '', title: hit.article?.title ?? '', page: null }
}

export type AnswerPart = { text: string; cite?: number }

/** Splits an answer on its [n] markers; markers that point at no passage stay plain text. */
export function splitCitations(answer: string, count: number): AnswerPart[] {
  const parts: AnswerPart[] = []
  let last = 0
  for (const match of answer.matchAll(/\[(\d{1,2})\]/g)) {
    const n = Number(match[1])
    if (n < 1 || n > count) continue
    if (match.index > last) parts.push({ text: answer.slice(last, match.index) })
    parts.push({ text: match[0], cite: n })
    last = match.index + match[0].length
  }
  if (last < answer.length) parts.push({ text: answer.slice(last) })
  return parts
}

export type SnippetPart = { text: string; hit: boolean }

const OPEN = '⟦'
const CLOSE = '⟧'

/** Splits a snippet on its ⟦ ⟧ markers so the highlights render as React nodes, never as injected HTML. */
export function splitHighlights(snippet: string): SnippetPart[] {
  const parts: SnippetPart[] = []
  let rest = snippet
  while (rest) {
    const open = rest.indexOf(OPEN)
    if (open === -1) break
    const close = rest.indexOf(CLOSE, open + 1)
    if (close === -1) break
    if (open > 0) parts.push({ text: rest.slice(0, open), hit: false })
    const hit = rest.slice(open + 1, close)
    if (hit) parts.push({ text: hit, hit: true })
    rest = rest.slice(close + 1)
  }
  const tail = rest.replaceAll(OPEN, '').replaceAll(CLOSE, '')
  if (tail) parts.push({ text: tail, hit: false })
  return parts
}
