import { createFileRoute } from '@tanstack/react-router'

import { AskPage } from '@/features/ai/ask-page'

export const Route = createFileRoute('/app/$ws/ask')({ component: AskPage })
