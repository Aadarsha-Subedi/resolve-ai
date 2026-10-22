import { createFileRoute } from '@tanstack/react-router'

import { InvitationsPage } from '@/features/workspaces/invitations-page'

export const Route = createFileRoute('/app/invitations')({ component: InvitationsPage })
