import { createFileRoute } from "@tanstack/react-router"
import { useDocumentTitle } from "@/hooks/use-document-title"
import { LandingPage } from "@/features/marketing/landing-page"

export const Route = createFileRoute("/")({ component: Page })

function Page() {
  useDocumentTitle("ResolveAI · The support desk that watches the clock")
  return <LandingPage />
}
