import { createFileRoute } from '@tanstack/react-router'

import { validateKnowledgeSearch } from '@/features/knowledge/search'
import { KnowledgePage } from '@/features/knowledge/knowledge-page'

export const Route = createFileRoute('/app/$ws/knowledge/')({
  validateSearch: validateKnowledgeSearch,
  component: Page,
})

function Page() {
  return <KnowledgePage search={Route.useSearch()} />
}
