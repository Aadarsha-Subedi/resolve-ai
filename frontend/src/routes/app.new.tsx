import { createFileRoute } from '@tanstack/react-router'

import { CreateWorkspacePage } from '@/features/workspaces/create-workspace-page'

export const Route = createFileRoute('/app/new')({ component: CreateWorkspacePage })
