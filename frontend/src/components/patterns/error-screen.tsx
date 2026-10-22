import { Button } from "@/components/ui/button"
import { ApiError } from "@/lib/api"
import { ArrowClockwise, House, Command, WarningCircle } from "@/icons"
import { cn } from "@/lib/utils"

function describe(error: unknown): { title: string; body: string } {
  if (error instanceof ApiError && error.status >= 500) return { title: "The server had a problem", body: "It isn't your fault, and nothing you did was lost. Try again in a moment." }
  if (error instanceof ApiError && error.code === "network_error") return { title: "Can't reach the server", body: "Check your connection and try again." }
  return { title: "Something went wrong", body: "This page failed to load. Reload it, or head home." }
}

/**
 * Router fallback for a page that threw while loading or rendering. Same frame as the not-found and boot screens:
 * the mark, one sentence, two ways out. The raw error stays out of sight; it goes to the console for developers.
 */
export function ErrorScreen({ error, className }: { error: unknown; reset?: () => void; className?: string }) {
  const { title, body } = describe(error)
  if (import.meta.env.DEV) console.error(error)
  return (
    <main role="alert" className={cn("grid min-h-[min(100dvh,36rem)] place-items-center bg-background px-6", className)}>
      <div className="flex w-full max-w-sm flex-col items-center gap-5 text-center">
        <span className="grid size-12 place-items-center rounded-xl bg-primary text-primary-foreground" aria-hidden>
          <Command weight="bold" className="size-7" />
        </span>
        <div className="space-y-2">
          <h1 className="text-lg font-semibold tracking-tight">{title}</h1>
          <p className="flex items-start justify-center gap-1.5 text-sm text-muted-foreground"><WarningCircle weight="fill" className="mt-0.5 size-4 shrink-0 text-warning" aria-hidden />{body}</p>
        </div>
        <div className="flex flex-wrap justify-center gap-2">
          <Button icon={<ArrowClockwise />} onClick={() => window.location.reload()}>Reload page</Button>
          <Button variant="outline" icon={<House />} nativeButton={false} render={<a href="/" />}>Take me home</Button>
        </div>
      </div>
    </main>
  )
}
