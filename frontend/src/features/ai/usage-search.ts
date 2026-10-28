import type { UsageFeature, UsageOutcome, UsageSearch } from '@/features/ai/usage-api'

export const FEATURE_LABELS: Record<UsageFeature, string> = {
  ask: 'Answer',
  rewrite: 'Query rewrite',
  rerank: 'Rerank',
  embedding: 'Embedding',
}
export const OUTCOME_LABELS: Record<UsageOutcome, string> = {
  cache_hit: 'From cache',
  llm_call: 'Sent to AI',
  error: 'Failed',
}

const ORDER_FIELDS = ['created_at', 'user', 'feature', 'outcome', 'tokens']
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const oneOf = <T extends string>(value: unknown, allowed: string[]): T | undefined => (typeof value === 'string' && allowed.includes(value) ? (value as T) : undefined)
const date = (value: unknown) => (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) ? value : undefined)

/** URL state of the usage log: unknown or malformed values are dropped instead of reaching the API. */
export function validateUsageSearch(search: Record<string, unknown>): UsageSearch {
  const page = Number(search.page)
  return {
    q: typeof search.q === 'string' && search.q.trim() ? search.q.trim().slice(0, 200) : undefined,
    feature: oneOf(search.feature, Object.keys(FEATURE_LABELS)),
    outcome: oneOf(search.outcome, Object.keys(OUTCOME_LABELS)),
    actor: typeof search.actor === 'string' && UUID.test(search.actor) ? search.actor : undefined,
    created_from: date(search.created_from),
    created_to: date(search.created_to),
    ordering: typeof search.ordering === 'string' && ORDER_FIELDS.includes(search.ordering.replace(/^-/, '')) ? search.ordering : undefined,
    page: Number.isInteger(page) && page > 1 ? page : undefined,
  }
}
