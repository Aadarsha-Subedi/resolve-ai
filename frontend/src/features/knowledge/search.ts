import type { ArticleStatus } from '@/features/knowledge/api'

export type KnowledgeSearch = { view?: 'graph'; title?: string; status?: ArticleStatus; category?: string; page?: number }

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

export function validateKnowledgeSearch(search: Record<string, unknown>): KnowledgeSearch {
  const page = Number(search.page)
  return {
    view: search.view === 'graph' ? 'graph' : undefined,
    title: typeof search.title === 'string' && search.title.trim() ? search.title.trim().slice(0, 200) : undefined,
    status: ['draft', 'published', 'archived'].includes(search.status as string) ? (search.status as ArticleStatus) : undefined,
    category: typeof search.category === 'string' && UUID.test(search.category) ? search.category : undefined,
    page: Number.isInteger(page) && page > 1 ? page : undefined,
  }
}
