import { createFileRoute } from '@tanstack/react-router'

import { AppLayout } from '@/features/app/app-layout'

export const Route = createFileRoute('/app')({ component: AppLayout })
