import { createFileRoute } from '@tanstack/react-router'

import { DashboardPage } from '@/features/dashboard/dashboard-page'
import { validateDashboardSearch } from '@/features/dashboard/search'

export const Route = createFileRoute('/app/$ws/')({
  validateSearch: validateDashboardSearch,
  component: Page,
})

function Page() {
  return <DashboardPage search={Route.useSearch()} />
}
