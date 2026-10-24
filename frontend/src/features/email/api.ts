import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api, apiList } from '@/lib/api'
import type { GmailConnection } from '@/lib/types'

export type ReviewItem = { id: string; sender_email: string; sender_name: string; subject: string; snippet: string; received_at: string }
export type SyncReport = { matched: number; needs_review: number; duplicates: number; ignored: number; limit: number }

export function useGmailStatus() {
  return useQuery({ queryKey: ['email', 'gmail'], queryFn: async () => (await api.get<GmailConnection>('/email/gmail/')).data })
}

export function useReviewItems() {
  return useQuery({ queryKey: ['email', 'review'], queryFn: async () => (await apiList<ReviewItem>('/email/review/', { limit: 100 })).items })
}

/** "Sync latest mails": the only way to pull mail on demand. Afterwards the two displayed queries are refetched once. */
export function useSyncMail() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: async () => (await api.post<SyncReport>('/email/gmail/sync/')).data,
    onSuccess: () => Promise.all([client.invalidateQueries({ queryKey: ['email', 'review'] }), client.invalidateQueries({ queryKey: ['email', 'gmail'] })]),
  })
}

export function useAttachReview() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, workspaceId, ticketId }: { id: string; workspaceId: string; ticketId: string }) => {
      await api.post(`/email/review/${id}/attach/`, { workspace_id: workspaceId, ticket_id: ticketId })
      return id
    },
    onSuccess: (id) => client.setQueryData<ReviewItem[]>(['email', 'review'], (list) => list?.filter((i) => i.id !== id)),
  })
}

export function useDismissReview() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      await api.post(`/email/review/${id}/dismiss/`)
      return id
    },
    onSuccess: (id) => client.setQueryData<ReviewItem[]>(['email', 'review'], (list) => list?.filter((i) => i.id !== id)),
  })
}
