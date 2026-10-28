import { createFileRoute } from '@tanstack/react-router'

import { UsagePage } from '@/features/ai/usage-page'
import { validateUsageSearch } from '@/features/ai/usage-search'

export const Route = createFileRoute('/app/$ws/ai-usage')({
  validateSearch: validateUsageSearch,
  component: Page,
})

function Page() {
  return <UsagePage search={Route.useSearch()} />
}
