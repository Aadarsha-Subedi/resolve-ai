import { createFileRoute } from "@tanstack/react-router"
import { redirectIfSignedIn } from "@/features/auth/guards"
import { useDocumentTitle } from "@/hooks/use-document-title"
import { LandingPage } from "@/features/marketing/landing-page"

export const Route = createFileRoute("/")({
  beforeLoad: redirectIfSignedIn,
  validateSearch: (search: Record<string, unknown>): { google_error?: string } => ({
    google_error: typeof search.google_error === "string" ? search.google_error : undefined,
  }),
  component: Page,
})

function Page() {
  const { google_error } = Route.useSearch()
  useDocumentTitle("ResolveAI · The support desk that watches the clock")
  return <LandingPage error={google_error} />
}
