import { Navigate } from '@tanstack/react-router'

import { Skeleton } from '@/components/ui/skeleton'
import { ErrorPanel } from '@/features/app/page-states'
import { getLastWorkspace, useWorkspaces } from '@/features/workspaces/api'

/** /app: the last used workspace (if you still belong to it), else your first one, else the create page. */
export function AppHome() {
  const { data, error, isPending, refetch } = useWorkspaces()
  if (isPending) return <div aria-busy="true" aria-label="Loading"><Skeleton className="h-8 w-56" /></div>
  if (error) return <ErrorPanel error={error} onRetry={() => void refetch()} title="Could not load your workspaces" />
  const last = getLastWorkspace()
  const target = data.find((w) => w.id === last) ?? data[0]
  return target ? <Navigate to={`/app/${target.id}` as never} replace /> : <Navigate to="/app/new" replace />
}
