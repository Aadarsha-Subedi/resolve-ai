import { useQuery } from '@tanstack/react-query'

import { apiList } from '@/lib/api'

export type AuditEvent = {
  id: string
  action: string
  actor: { id: string | null; name: string } | null
  target: { type: string; id: string } | null
  metadata: Record<string, unknown>
  created_at: string
}

export const AUDIT_PAGE_SIZE = 25
export type AuditFilters = { action_prefix?: string; created_from?: string; created_to?: string; page?: number }

export function useAuditEvents(ws: string, filters: AuditFilters, enabled: boolean) {
  const { page = 1, ...rest } = filters
  const query = { ...rest, limit: AUDIT_PAGE_SIZE, offset: (page - 1) * AUDIT_PAGE_SIZE }
  return useQuery({
    queryKey: ['ws', ws, 'audit', query],
    enabled,
    queryFn: ({ signal }) => apiList<AuditEvent>(`/workspaces/${ws}/audit/`, query, signal),
  })
}
