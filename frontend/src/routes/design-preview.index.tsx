import { createFileRoute } from "@tanstack/react-router"
import { useDocumentTitle } from "@/hooks/use-document-title"
import { DesignPreview } from "@/features/design-preview/preview-page"

export const Route = createFileRoute("/design-preview/")({
  component: Page,
})

function Page() {
  useDocumentTitle("Design preview · ResolveAI")
  return <DesignPreview />
}
