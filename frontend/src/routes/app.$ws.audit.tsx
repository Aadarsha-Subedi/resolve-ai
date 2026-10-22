import { createFileRoute } from '@tanstack/react-router'

import { AuditPage } from '@/features/audit/audit-page'
import { validateAuditSearch } from '@/features/audit/search'

export const Route = createFileRoute('/app/$ws/audit')({
  validateSearch: validateAuditSearch,
  component: Page,
})

function Page() {
  return <AuditPage search={Route.useSearch()} />
}
