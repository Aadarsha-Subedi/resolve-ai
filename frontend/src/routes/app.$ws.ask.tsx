import { createFileRoute } from '@tanstack/react-router'

import { AskPage } from '@/features/ai/ask-page'

function AskRoute() {
  const { q } = Route.useSearch()
  return <AskPage initialQuestion={q} />
}

export const Route = createFileRoute('/app/$ws/ask')({
  validateSearch: (search: Record<string, unknown>): { q?: string } => ({ q: typeof search.q === 'string' && search.q.trim() ? search.q.slice(0, 5000) : undefined }),
  component: AskRoute,
})
