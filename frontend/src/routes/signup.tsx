import { createFileRoute } from "@tanstack/react-router"
import { useDocumentTitle } from "@/hooks/use-document-title"
import { AuthPage } from "@/features/marketing/auth-page"

export const Route = createFileRoute("/signup")({
  component: Page,
  validateSearch: (search: Record<string, unknown>): { google_error?: string } => ({
    google_error: typeof search.google_error === "string" ? search.google_error : undefined,
  }),
})

function Page() {
  const { google_error } = Route.useSearch()
  useDocumentTitle("Sign up · ResolveAI")
  return <AuthPage mode="signup" error={google_error} />
}
