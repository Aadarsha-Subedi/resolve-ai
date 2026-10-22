import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '@/lib/api'
import { ensureCsrfCookie, type CurrentUser } from '@/features/auth/api'

export type DeviceSession = { id: number; device: string; created_at: string; last_active_at: string; is_current: boolean }

export function useSessions(enabled = true) {
  return useQuery({
    queryKey: ['auth', 'sessions'],
    enabled,
    queryFn: async () => (await api.get<{ items: DeviceSession[] }>('/auth/sessions/')).data.items,
  })
}

export function useRevokeSession() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => api.delete(`/auth/sessions/${id}/`),
    onSuccess: (_result, id) => client.setQueryData<DeviceSession[]>(['auth', 'sessions'], (list) => list?.filter((s) => s.id !== id)),
  })
}

export function useUpdateProfile() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: async (display_name: string) => (await api.patch<CurrentUser>('/me/', { display_name })).data,
    onSuccess: (user) => client.setQueryData(['auth', 'me'], user),
  })
}

export function useDeleteAccount() {
  return useMutation({ mutationFn: async () => (await api.delete<{ detail: string }>('/me/')).message })
}

/** Signs out, then sends the browser to the sign-in page (a full load clears every cache). */
export function useSignOut(everywhere = false) {
  return useMutation({
    mutationFn: async () => {
      await ensureCsrfCookie()
      await api.post(everywhere ? '/auth/logout-all/' : '/auth/logout/')
    },
    onSuccess: () => window.location.assign('/login'),
  })
}

