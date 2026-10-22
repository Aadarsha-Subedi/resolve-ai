import { createFileRoute } from '@tanstack/react-router'

import { validateTicketSearch } from '@/features/tickets/search'
import { TicketsPage } from '@/features/tickets/tickets-page'

export const Route = createFileRoute('/app/$ws/tickets/')({
  validateSearch: validateTicketSearch,
  component: Page,
})

function Page() {
  const search = Route.useSearch()
  return <TicketsPage search={search} />
}
