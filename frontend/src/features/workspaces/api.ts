import { queryOptions, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { ApiError, api, apiList } from '@/lib/api'
import type { Role, Workspace } from '@/lib/types'

/** GET /workspaces/ (the signed-in user's workspaces, each with their role). The source of truth for roles. */
export const workspacesQuery = queryOptions({
  queryKey: ['workspaces'],
  queryFn: async () => (await apiList<Workspace>('/workspaces/', { limit: 100 })).items,
})

export function useWorkspaces() {
  return useQuery(workspacesQuery)
}

const LAST_KEY = 'resolveai-last-workspace'

export function getLastWorkspace(): string | null {
  try {
    return localStorage.getItem(LAST_KEY)
  } catch {
    return null
  }
}

export function setLastWorkspace(id: string) {
  try {
    localStorage.setItem(LAST_KEY, id)
  } catch {
    /* storage unavailable */
  }
}

export type CurrentWorkspace =
  | { state: 'loading' }
  | { state: 'error'; error: unknown }
  | { state: 'missing' }
  | { state: 'ready'; workspace: Workspace; isOwner: boolean; role: Role }

/** The workspace for a route, looked up in the list the app already loaded; "missing" shows the 404 screen. */
export function useCurrentWorkspace(workspaceId: string): CurrentWorkspace {
  const { data, isPending, error } = useWorkspaces()
  if (isPending) return { state: 'loading' }
  if (error) return { state: 'error', error }
  const workspace = data?.find((w) => w.id === workspaceId)
  if (!workspace) return { state: 'missing' }
  return { state: 'ready', workspace, isOwner: workspace.role === 'owner', role: workspace.role }
}

/** Replaces one workspace in the cached list (used after a write that returns the workspace). */
export function useWorkspaceCache() {
  const client = useQueryClient()
  return {
    put(workspace: Workspace) {
      client.setQueryData<Workspace[]>(['workspaces'], (list) => {
        if (!list) return list
        return list.some((w) => w.id === workspace.id) ? list.map((w) => (w.id === workspace.id ? workspace : w)) : [workspace, ...list]
      })
    },
    remove(id: string) {
      client.setQueryData<Workspace[]>(['workspaces'], (list) => list?.filter((w) => w.id !== id))
    },
  }
}

export function useCreateWorkspace() {
  const cache = useWorkspaceCache()
  return useMutation({
    mutationFn: async (body: { name: string; slug?: string }) => (await api.post<Workspace>('/workspaces/', body)).data,
    onSuccess: (workspace) => cache.put(workspace),
  })
}

export function useRedeemJoinLink() {
  const cache = useWorkspaceCache()
  return useMutation({
    mutationFn: async (token: string) => {
      const result = await api.post<Workspace>('/join-links/redeem/', { token })
      return { workspace: result.data, joined: Boolean(result.meta.joined) }
    },
    onSuccess: ({ workspace }) => cache.put(workspace),
  })
}

export type MyInvitation = { id: string; workspace: { id: string; name: string; slug: string }; expires_at: string | null }

export const invitationsQuery = queryOptions({
  queryKey: ['invitations', 'mine'],
  queryFn: async () => (await apiList<MyInvitation>('/invitations/', { limit: 100 })).items,
})

export function useMyInvitations() {
  return useQuery(invitationsQuery)
}

export function useAnswerInvitation() {
  const client = useQueryClient()
  const cache = useWorkspaceCache()
  return useMutation({
    mutationFn: async ({ id, accept }: { id: string; accept: boolean }) => {
      const result = await api.post<Workspace | Record<string, never>>(`/invitations/${id}/${accept ? 'accept' : 'decline'}/`)
      return { id, workspace: accept ? (result.data as Workspace) : null }
    },
    onSuccess: ({ id, workspace }) => {
      client.setQueryData<MyInvitation[]>(['invitations', 'mine'], (list) => list?.filter((i) => i.id !== id))
      if (workspace) cache.put(workspace)
    },
  })
}

// ---- members, join link, invitations, settings (each panel's hooks are enabled only while it is open) ----

export type Member = { user_id: string; email: string; display_name: string; avatar_url: string | null; role: Role; joined_at: string }
export type JoinLinkStatus = { active: boolean; created_at?: string; expires_at?: string }
export type IssuedJoinLink = JoinLinkStatus & { token: string; url: string }
export type WorkspaceInvitation = { id: string; email: string; created_at: string; expires_at: string }
export type InvitationOutcome = { email: string; outcome: string; invitation: WorkspaceInvitation | null }

const wsKey = (id: string) => ['ws', id] as const

export function useMembers(ws: string) {
  return useQuery({
    queryKey: [...wsKey(ws), 'members'],
    queryFn: async () => (await apiList<Member>(`/workspaces/${ws}/members/`, { limit: 100 })).items,
  })
}

export function useRemoveMember(ws: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: async (userId: string) => {
      await api.delete(`/workspaces/${ws}/members/${userId}/`)
      return userId
    },
    onSuccess: (userId) => {
      client.setQueryData<Member[]>([...wsKey(ws), 'members'], (list) => list?.filter((m) => m.user_id !== userId))
      // The server unassigns the removed member's active tickets: cached ticket lists are stale, none refetches until opened.
      void client.invalidateQueries({ queryKey: [...wsKey(ws), 'tickets'], refetchType: 'none' })
    },
  })
}

export function useTransferOwnership(ws: string) {
  const client = useQueryClient()
  const cache = useWorkspaceCache()
  return useMutation({
    mutationFn: async (userId: string) => (await api.post<Workspace>(`/workspaces/${ws}/transfer-ownership/`, { user_id: userId })).data,
    onSuccess: (workspace, userId) => {
      cache.put(workspace)
      client.setQueryData<Member[]>([...wsKey(ws), 'members'], (list) => list?.map((m) => (m.user_id === userId ? { ...m, role: 'owner' } : m.role === 'owner' ? { ...m, role: 'member' } : m)))
    },
  })
}

export function useLeaveWorkspace(ws: string) {
  const cache = useWorkspaceCache()
  return useMutation({
    mutationFn: () => api.post(`/workspaces/${ws}/leave/`),
    onSuccess: () => cache.remove(ws),
  })
}

export function useJoinLink(ws: string, enabled: boolean) {
  return useQuery({
    queryKey: [...wsKey(ws), 'join-link'],
    enabled,
    queryFn: async () => (await api.get<JoinLinkStatus>(`/workspaces/${ws}/join-link/`)).data,
  })
}

export function useCreateJoinLink(ws: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: async (expires_in: '1h' | '1d' | '7d') => (await api.post<IssuedJoinLink>(`/workspaces/${ws}/join-link/`, { expires_in })).data,
    onSuccess: (issued) => client.setQueryData<JoinLinkStatus>([...wsKey(ws), 'join-link'], { active: true, created_at: issued.created_at, expires_at: issued.expires_at }),
  })
}

export function useRevokeJoinLink(ws: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: () => api.delete(`/workspaces/${ws}/join-link/`),
    onSuccess: () => client.setQueryData<JoinLinkStatus>([...wsKey(ws), 'join-link'], { active: false }),
  })
}

export function useWorkspaceInvitations(ws: string, enabled: boolean) {
  return useQuery({
    queryKey: [...wsKey(ws), 'invitations'],
    enabled,
    queryFn: async () => (await apiList<WorkspaceInvitation>(`/workspaces/${ws}/invitations/`, { limit: 100 })).items,
  })
}

export function useCreateInvitations(ws: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: async (emails: string[]) => (await api.post<{ items: InvitationOutcome[] }>(`/workspaces/${ws}/invitations/`, { emails })).data.items,
    // The list on screen is the only thing this changes, so it is the only thing refetched.
    onSuccess: () => client.invalidateQueries({ queryKey: [...wsKey(ws), 'invitations'] }),
  })
}

export function useRevokeInvitation(ws: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/workspaces/${ws}/invitations/${id}/`)
      return id
    },
    onSuccess: (id) => client.setQueryData<WorkspaceInvitation[]>([...wsKey(ws), 'invitations'], (list) => list?.filter((i) => i.id !== id)),
  })
}

export function useUpdateWorkspace(ws: string) {
  const cache = useWorkspaceCache()
  return useMutation({
    mutationFn: async (changes: { name?: string; portal_enabled?: boolean }) => (await api.patch<Workspace>(`/workspaces/${ws}/`, changes)).data,
    onSuccess: (workspace) => cache.put(workspace),
  })
}

export function useDeleteWorkspace(ws: string) {
  const cache = useWorkspaceCache()
  return useMutation({
    mutationFn: async () => (await api.delete(`/workspaces/${ws}/`)).message,
    onSuccess: () => cache.remove(ws),
  })
}

/** Logo: signed URL, PUT the image straight to storage, then confirm with the returned key. */
export function useUploadLogo(ws: string) {
  const cache = useWorkspaceCache()
  return useMutation({
    mutationFn: async (file: File) => {
      const signed = (await api.post<{ key: string; upload_url: string; headers: Record<string, string> }>(`/workspaces/${ws}/logo/upload-url/`, { content_type: file.type, size: file.size })).data
      let response: Response
      try {
        response = await fetch(signed.upload_url, { method: 'PUT', headers: signed.headers, body: file })
      } catch {
        throw new ApiError(0, 'The image could not be sent to storage. Check your connection and try again.', 'network_error')
      }
      if (!response.ok) throw new ApiError(response.status, 'Storage rejected the image. Try again.', 'upload_failed')
      return (await api.put<Workspace>(`/workspaces/${ws}/logo/`, { key: signed.key })).data
    },
    onSuccess: (workspace) => cache.put(workspace),
  })
}

export function useRemoveLogo(ws: string) {
  const client = useQueryClient()
  const cache = useWorkspaceCache()
  return useMutation({
    mutationFn: () => api.delete(`/workspaces/${ws}/logo/`),
    onSuccess: () => {
      const current = client.getQueryData<Workspace[]>(['workspaces'])?.find((w) => w.id === ws)
      if (current) cache.put({ ...current, logo_url: null })
    },
  })
}
