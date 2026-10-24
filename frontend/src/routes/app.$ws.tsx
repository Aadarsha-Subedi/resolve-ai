import { createFileRoute } from '@tanstack/react-router'

import { WorkspaceRoute } from '@/features/app/workspace-route'

export const Route = createFileRoute('/app/$ws')({ component: Page })

function Page() {
  const { ws } = Route.useParams()
  return <WorkspaceRoute workspaceId={ws} />
}
