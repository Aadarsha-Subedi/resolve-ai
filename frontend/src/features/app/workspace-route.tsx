import { Outlet } from '@tanstack/react-router'
import { useEffect, useMemo } from 'react'

import { NotFoundScreen } from '@/components/patterns/not-found-screen'
import { Skeleton } from '@/components/ui/skeleton'
import { ErrorPanel } from '@/features/app/page-states'
import { WorkspaceContext } from '@/features/app/workspace-context'
import { setLastWorkspace, useCurrentWorkspace, useWorkspaces } from '@/features/workspaces/api'

/** Layout of /app/$ws: looks the workspace up in the cached list; unknown or non-member ids show the 404 screen. */
export function WorkspaceRoute({ workspaceId }: { workspaceId: string }) {
  const current = useCurrentWorkspace(workspaceId)
  const { refetch } = useWorkspaces()
  const ready = current.state === 'ready' ? current : null
  useEffect(() => {
    if (ready) setLastWorkspace(ready.workspace.id)
  }, [ready])
  const value = useMemo(() => (ready ? { workspace: ready.workspace, role: ready.role, isOwner: ready.isOwner } : null), [ready])

  if (current.state === 'loading') return <div className="space-y-4" aria-busy="true" aria-label="Loading"><Skeleton className="h-8 w-56" /><Skeleton className="h-48 w-full" /></div>
  if (current.state === 'error') return <ErrorPanel error={current.error} onRetry={() => void refetch()} title="Could not load your workspaces" />
  if (current.state === 'missing' || !value) return <NotFoundScreen className="min-h-[60vh]" />
  return (
    <WorkspaceContext.Provider value={value}>
      <Outlet />
    </WorkspaceContext.Provider>
  )
}
