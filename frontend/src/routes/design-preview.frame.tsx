import { createFileRoute } from "@tanstack/react-router"
import { useDocumentTitle } from "@/hooks/use-document-title"
import { FramePreview } from "@/features/design-preview/frame-page"

export const Route = createFileRoute("/design-preview/frame")({
  component: Page,
})

function Page() {
  useDocumentTitle("App frame · ResolveAI")
  return <FramePreview />
}
