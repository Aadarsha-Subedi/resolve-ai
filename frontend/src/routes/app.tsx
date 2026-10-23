import { createFileRoute } from '@tanstack/react-router'

import { AppLayout } from '@/features/app/app-layout'
import { requireSignedIn } from '@/features/auth/guards'

export const Route = createFileRoute('/app')({ beforeLoad: requireSignedIn, component: AppLayout })
