import { useMutation, useQuery } from '@tanstack/react-query'

import { api } from '@/lib/api'
import type { TicketCategoryValue } from '@/lib/types'

export type PortalInfo = { name: string; slug: string; logo_url: string | null }

export function usePortal(slug: string) {
  return useQuery({
    queryKey: ['portal', slug],
    queryFn: async ({ signal }) => (await api.get<PortalInfo>(`/portal/${slug}/`, undefined, signal)).data,
  })
}

export type PortalTicket = { subject: string; description: string; customer_email: string; customer_name?: string; category?: TicketCategoryValue; website: string }

export function useSubmitPortalTicket(slug: string) {
  return useMutation({
    mutationFn: async (body: PortalTicket) => (await api.post<{ number: number }>(`/portal/${slug}/tickets/`, body)).data.number,
  })
}
