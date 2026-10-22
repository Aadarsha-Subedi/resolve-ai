import { createFileRoute } from '@tanstack/react-router'

import { JoinPage } from '@/features/workspaces/join-page'

export const Route = createFileRoute('/join/$token')({ component: Page })

function Page() {
  const { token } = Route.useParams()
  return <JoinPage token={token} />
}
