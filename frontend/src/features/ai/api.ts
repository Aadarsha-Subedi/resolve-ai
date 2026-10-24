import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '@/lib/api'

export type LlmMode = 'resolve_ai' | 'own_key'
export type LlmProvider = 'gemini' | 'openai'

export type LlmKey = { provider: LlmProvider; model: string; last4: string; checked_at: string }

export type LlmSettings = {
  mode: LlmMode
  resolve_ai_model: string
  /** Which saved key answers in own-key mode. */
  active_provider: LlmProvider | null
  keys: LlmKey[]
  usage: { used_today: number; limit: number; remaining: number; resets_at: string }
  options: {
    resolve_ai: { available: boolean; models: string[] }
    providers: Record<LlmProvider, { models: string[]; default: string }>
  }
}

export type LlmSettingsChange = Partial<{ mode: LlmMode; resolve_ai_model: string; active_provider: LlmProvider }>
/** `api_key` is write-only and never comes back. A new key needs it; an edit may send only `model`. */
export type LlmKeyChange = { provider: LlmProvider; api_key?: string; model?: string }

const llmKey = (ws: string) => ['ws', ws, 'llm'] as const

/** The signed-in user's AI settings for one workspace (they are per user, per workspace). */
export function useLlmSettings(ws: string) {
  return useQuery({
    queryKey: llmKey(ws),
    queryFn: async ({ signal }) => (await api.get<LlmSettings>(`/workspaces/${ws}/llm/`, undefined, signal)).data,
  })
}

export function useUpdateLlmSettings(ws: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: async (body: LlmSettingsChange) => (await api.patch<LlmSettings>(`/workspaces/${ws}/llm/`, body)).data,
    onSuccess: (data) => client.setQueryData(llmKey(ws), data),
  })
}

/** Adds the key for a provider, or edits it. The server checks the key with the provider first. */
export function useSaveLlmKey(ws: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: async ({ provider, ...body }: LlmKeyChange) => (await api.put<LlmSettings>(`/workspaces/${ws}/llm/keys/${provider}/`, body)).data,
    onSuccess: (data) => client.setQueryData(llmKey(ws), data),
  })
}

export function useRemoveLlmKey(ws: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: async (provider: LlmProvider) => (await api.delete<LlmSettings>(`/workspaces/${ws}/llm/keys/${provider}/`)).data,
    onSuccess: (data) => client.setQueryData(llmKey(ws), data),
  })
}

/** After a search that may have spent allowance: refetch the usage if a page is showing it, else just mark it stale. */
export function useRefreshLlmUsage(ws: string) {
  const client = useQueryClient()
  return () => void client.invalidateQueries({ queryKey: llmKey(ws) })
}

/** Today's allowance was spent or changed by a context search; the next view of the settings should refetch it. */
export function useStaleLlmUsage(ws: string) {
  const client = useQueryClient()
  return () => void client.invalidateQueries({ queryKey: llmKey(ws), refetchType: 'none' })
}

export const PROVIDER_LABELS: Record<LlmProvider, string> = { gemini: 'Google Gemini', openai: 'OpenAI' }
