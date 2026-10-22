import { createFileRoute } from '@tanstack/react-router'

import { NewArticlePage } from '@/features/knowledge/article-page'

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

export const Route = createFileRoute('/app/$ws/knowledge/new')({
  // The category chosen in the New dialog; anything that is not an id is dropped.
  validateSearch: (search: Record<string, unknown>): { category?: string } => ({ category: typeof search.category === 'string' && UUID.test(search.category) ? search.category : undefined }),
  component: Page,
})

function Page() {
  return <NewArticlePage initialCategory={Route.useSearch().category} />
}
