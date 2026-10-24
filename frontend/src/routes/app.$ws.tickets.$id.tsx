import { createFileRoute } from '@tanstack/react-router'

import { TicketPage } from '@/features/tickets/ticket-page'

export const Route = createFileRoute('/app/$ws/tickets/$id')({ component: Page })

function Page() {
  const { id } = Route.useParams()
  return <TicketPage key={id} ticketId={id} />
}
