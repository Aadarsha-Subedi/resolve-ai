import { createFileRoute } from '@tanstack/react-router'

import { EmailPage } from '@/features/email/email-page'

export const Route = createFileRoute('/app/email')({ component: EmailPage })
