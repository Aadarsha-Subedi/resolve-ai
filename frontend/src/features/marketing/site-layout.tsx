import type { ReactNode } from "react"
import { Link } from "@tanstack/react-router"
import { Logo } from "@/components/patterns/logo"
import { ThemeToggle } from "@/components/patterns/theme-toggle"
import { Button } from "@/components/ui/button"
import { ArrowRight } from "@/icons"

/** Public pages: a quiet top bar with the two entry points, the page, and a footer carrying the legal links. */
export function SiteLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-svh flex-col bg-background">
      <header className="sticky top-0 z-30 border-b bg-background/90 backdrop-blur-sm">
        <div className="mx-auto flex h-14 w-full max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
          <Link to="/" aria-label="ResolveAI home"><Logo /></Link>
          <nav aria-label="Account" className="flex items-center gap-1.5">
            <ThemeToggle />
            <Button variant="ghost" render={<Link to="/login" />} slide={false}>Sign in</Button>
            <Button iconEnd={<ArrowRight weight="bold" />} render={<Link to="/signup" />}>Get started</Button>
          </nav>
        </div>
      </header>
      <main className="flex-1">{children}</main>
      <SiteFooter />
    </div>
  )
}

export function SiteFooter() {
  return (
    <footer className="border-t">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-4 px-4 py-8 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <Logo className="text-foreground" />
        <nav aria-label="Legal" className="flex items-center gap-5">
          <Link to="/terms" className="underline-offset-4 hover:text-foreground hover:underline">Terms</Link>
          <Link to="/privacy" className="underline-offset-4 hover:text-foreground hover:underline">Privacy</Link>
        </nav>
        <p>© {new Date().getFullYear()} ResolveAI</p>
      </div>
    </footer>
  )
}
