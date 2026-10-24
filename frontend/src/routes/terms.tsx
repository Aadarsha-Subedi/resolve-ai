import { createFileRoute } from "@tanstack/react-router"
import { useDocumentTitle } from "@/hooks/use-document-title"
import { LegalPage } from "@/features/marketing/legal-page"
import { TERMS, UPDATED } from "@/features/marketing/legal-content"

export const Route = createFileRoute("/terms")({ component: Page })

function Page() {
  useDocumentTitle("Terms of Service · ResolveAI")
  return <LegalPage {...TERMS} updated={UPDATED} />
}
