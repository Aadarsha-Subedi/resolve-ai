import { createContext, useContext } from 'react'

import type { Role, Workspace } from '@/lib/types'

export type WorkspaceState = { workspace: Workspace; role: Role; isOwner: boolean }

export const WorkspaceContext = createContext<WorkspaceState | null>(null)

/** The workspace of the current route. Its role comes from GET /workspaces/, never guessed. */
export function useWorkspace(): WorkspaceState {
  const value = useContext(WorkspaceContext)
  if (!value) throw new Error('useWorkspace outside a workspace route')
  return value
}

export const OWNER_ONLY = 'Only the workspace owner can do this.'
