import { createFileRoute } from '@tanstack/react-router'

import { PortalPage } from '@/features/portal/portal-page'

export const Route = createFileRoute('/portal/$slug')({ component: Page })

function Page() {
  const { slug } = Route.useParams()
  return <PortalPage slug={slug} />
}
