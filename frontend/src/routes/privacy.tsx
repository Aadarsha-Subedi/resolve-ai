import { createFileRoute } from "@tanstack/react-router"
import { useDocumentTitle } from "@/hooks/use-document-title"
import { LegalPage } from "@/features/marketing/legal-page"
import { PRIVACY, UPDATED } from "@/features/marketing/legal-content"

export const Route = createFileRoute("/privacy")({ component: Page })

function Page() {
  useDocumentTitle("Privacy Policy · ResolveAI")
  return <LegalPage {...PRIVACY} updated={UPDATED} />
}
