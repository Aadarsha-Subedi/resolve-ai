import { createFileRoute } from '@tanstack/react-router'

import { MembersPage } from '@/features/workspaces/members-page'

export const Route = createFileRoute('/app/$ws/members')({ component: MembersPage })
