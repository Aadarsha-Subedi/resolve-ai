import { createFileRoute } from '@tanstack/react-router'

import { SettingsPage } from '@/features/workspaces/settings-page'

export const Route = createFileRoute('/app/$ws/settings')({ component: SettingsPage })
