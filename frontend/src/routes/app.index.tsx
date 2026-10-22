import { createFileRoute } from '@tanstack/react-router'

import { AppHome } from '@/features/app/app-home'

export const Route = createFileRoute('/app/')({ component: AppHome })
