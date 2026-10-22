import { useMutation, useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query'
import { useCallback, useState } from 'react'

import { api, apiList } from '@/lib/api'
import type { GmailConnection, TicketCategoryValue, TicketDetail, TicketEvent, TicketMessage, TicketPriorityValue, TicketStatusValue, TicketSummary } from '@/lib/types'

export const PAGE_SIZE = 25

export type TicketFilters = {
  status?: TicketStatusValue
  priority?: TicketPriorityValue
  category?: TicketCategoryValue
  created_from?: string
  created_to?: string
  q?: string
  waiting_for_reply?: boolean
  assignee?: string
  ordering?: string
  page?: number
}

const ticketsKey = (ws: string) => ['ws', ws, 'tickets'] as const

export function useTickets(ws: string, filters: TicketFilters) {
  const { page = 1, waiting_for_reply, ...rest } = filters
  const query = { ...rest, waiting_for_reply: waiting_for_reply ? true : undefined, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE }
  return useQuery({
    queryKey: [...ticketsKey(ws), 'list', query],
    queryFn: ({ signal }) => apiList<TicketSummary>(`/workspaces/${ws}/tickets/`, query, signal),
  })
}

/** Lists become stale after a write, but only the one on screen would refetch (none, when the user is elsewhere). */
function staleLists(client: QueryClient, ws: string) {
  void client.invalidateQueries({ queryKey: [...ticketsKey(ws), 'list'], refetchType: 'none' })
}

export type NewTicket = { subject: string; description: string; customer_email: string; customer_name?: string; category: TicketCategoryValue; priority: TicketPriorityValue }

export function useCreateTicket(ws: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: async (body: NewTicket) => (await api.post<TicketDetail>(`/workspaces/${ws}/tickets/`, body)).data,
    onSuccess: () => staleLists(client, ws),
  })
}

export type TicketOverview = {
  ticket: TicketDetail
  viewer: { role: 'owner' | 'member'; permissions: string[] }
  messages: TicketMessage[]
  events: TicketEvent[]
  meta: { messages_total: number; messages_returned: number; events_total: number; events_returned: number }
  email: GmailConnection
}

const overviewKey = (ws: string, id: string) => [...ticketsKey(ws), 'overview', id] as const

/** The whole ticket page in one call. */
export function useTicketOverview(ws: string, id: string) {
  return useQuery({
    queryKey: overviewKey(ws, id),
    queryFn: async ({ signal }) => (await api.get<TicketOverview>(`/workspaces/${ws}/tickets/${id}/overview/`, undefined, signal)).data,
  })
}

/** After a write, the displayed overview is refetched once (it carries the new history entry); other lists just go stale. */
function afterWrite(client: QueryClient, ws: string, id: string) {
  staleLists(client, ws)
  return client.invalidateQueries({ queryKey: overviewKey(ws, id) })
}

export function useChangeStatus(ws: string, id: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: async (status: TicketStatusValue) => (await api.post<TicketDetail>(`/workspaces/${ws}/tickets/${id}/status/`, { status })).data,
    onSuccess: () => afterWrite(client, ws, id),
  })
}

/** `null` unassigns. */
export function useAssignTicket(ws: string, id: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: async (assignee: string | null) => (await api.post<TicketDetail>(`/workspaces/${ws}/tickets/${id}/assignee/`, { assignee })).data,
    onSuccess: () => afterWrite(client, ws, id),
  })
}

export type TicketChanges = Partial<Pick<NewTicket, 'subject' | 'description' | 'customer_email' | 'customer_name' | 'category' | 'priority'>>

export function useUpdateTicket(ws: string, id: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: async (changes: TicketChanges) => (await api.patch<TicketDetail>(`/workspaces/${ws}/tickets/${id}/`, changes)).data,
    onSuccess: () => afterWrite(client, ws, id),
  })
}

export function useAddMessage(ws: string, id: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: async (body: { body: string; visibility: 'public' | 'internal' }) => (await api.post<TicketMessage>(`/workspaces/${ws}/tickets/${id}/messages/`, body)).data,
    onSuccess: () => afterWrite(client, ws, id),
  })
}

export function useResendMessage(ws: string, id: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: async (messageId: string) => (await api.post<TicketMessage>(`/workspaces/${ws}/tickets/${id}/messages/${messageId}/resend/`)).data,
    onSuccess: () => afterWrite(client, ws, id),
  })
}

/**
 * "Load older": the overview holds the newest N items; the paginated list is oldest-first, so the
 * older ones are the first `total - returned`. Fetched on click only, kept in component state.
 */
export function useOlder<T>(path: string, total: number, returned: number) {
  const [older, setOlder] = useState<T[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const remaining = Math.max(0, total - returned - older.length)
  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const limit = Math.min(100, remaining)
      const offset = remaining - limit
      const page = await apiList<T>(path, { limit, offset })
      setOlder((current) => [...page.items, ...current])
    } catch (e) {
      setError(e)
    } finally {
      setLoading(false)
    }
  }, [path, remaining])
  return { older, remaining, loading, error, load }
}
