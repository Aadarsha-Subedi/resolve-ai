import { useMutation } from '@tanstack/react-query'

import { useRefreshLlmUsage } from '@/features/ai/api'
import { api } from '@/lib/api'

export const DRAFT_INTENT_MAX = 200

export type DraftSource = { article_id: string; title: string; section: string }
export type DraftReply = { draft: string; sources: DraftSource[] }

/** A short summary of the public conversation. Generated on demand, never stored. */
export function useSummarizeTicket(ws: string, ticketId: string) {
  const refreshUsage = useRefreshLlmUsage(ws)
  return useMutation({
    mutationFn: async () => (await api.post<{ summary: string }>(`/workspaces/${ws}/tickets/${ticketId}/summary/`, {})).data.summary,
    onSettled: refreshUsage,
  })
}

/** A draft email reply from the public conversation, matching articles and the agent's one-line instruction. */
export function useDraftReply(ws: string, ticketId: string) {
  const refreshUsage = useRefreshLlmUsage(ws)
  return useMutation({
    mutationFn: async (intent: string) => (await api.post<DraftReply>(`/workspaces/${ws}/tickets/${ticketId}/draft-reply/`, { intent })).data,
    onSettled: refreshUsage,
  })
}
