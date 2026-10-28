import { useQuery } from '@tanstack/react-query'

import { api, type ListMeta } from '@/lib/api'

export type UsageFeature = 'ask' | 'rewrite' | 'rerank' | 'embedding'
export type UsageOutcome = 'cache_hit' | 'llm_call' | 'error'

export type UsagePassage = { citation: number; title: string; section: string; page: number | null; cited: boolean }

export type UsageLog = {
  id: string
  feature: UsageFeature
  outcome: UsageOutcome
  user: { id: string; name: string } | null
  provider: string
  model: string
  question: string
  answer: string
  details: { status?: string; passages?: UsagePassage[]; similarity?: number; cached_question?: string; texts?: number }
  input_tokens: number
  output_tokens: number
  error_code: string
  created_at: string
}

export type UsageSummary = { total: number; cache_hits: number; llm_calls: number; errors: number; hit_rate: number | null }
export type UsageSearch = {
  q?: string
  feature?: UsageFeature
  outcome?: UsageOutcome
  actor?: string
  created_from?: string
  created_to?: string
  ordering?: string
  page?: number
}

export const USAGE_PAGE_SIZE = 25

/** One page of the owner-only AI usage log, plus the hit/miss counts of the filtered rows. */
export function useAiUsage(ws: string, search: UsageSearch, enabled: boolean) {
  const { page = 1, q, ...rest } = search
  const query = { ...rest, search: q, limit: USAGE_PAGE_SIZE, offset: (page - 1) * USAGE_PAGE_SIZE }
  return useQuery({
    queryKey: ['ws', ws, 'ai-usage', query],
    enabled,
    queryFn: async ({ signal }) => {
      const result = await api.get<{ items: UsageLog[] }>(`/workspaces/${ws}/ai/usage/`, query, signal)
      return { items: result.data.items, meta: result.meta as unknown as ListMeta & { summary: UsageSummary } }
    },
  })
}
