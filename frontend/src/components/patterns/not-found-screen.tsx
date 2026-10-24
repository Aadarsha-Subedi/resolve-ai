import { Link, useRouter } from "@tanstack/react-router"
import { Button } from "@/components/ui/button"
import { ArrowLeft, House, Command } from "@/icons"
import { cn } from "@/lib/utils"

/**
 * Page not found. Same frame as the boot screen: the mark, one sentence, two ways out.
 * Home is `/`, which sends a signed-in person on to their projects, so one button serves everyone.
 * `path` shows what was asked for, since a mistyped link is the usual cause.
 */
export function NotFoundScreen({ path, onBack, className }: { path?: string; onBack?: () => void; className?: string }) {
  const router = useRouter()
  const location = path ?? router.state.location.pathname
  return (
    <main className={cn("grid min-h-[min(100dvh,36rem)] place-items-center bg-background px-6", className)}>
      <div className="flex w-full max-w-sm flex-col items-center gap-5 text-center">
        <span className="grid size-12 place-items-center rounded-xl bg-primary text-primary-foreground" aria-hidden>
          <Command weight="bold" className="size-7" />
        </span>
        <div className="space-y-2">
          <h1 className="text-lg font-semibold tracking-tight">Page not found</h1>
          <p className="text-sm text-muted-foreground">That link doesn't lead anywhere. It may have moved, been deleted, or belong to a project you aren't in.</p>
          <p className="truncate font-mono text-xs text-muted-foreground" title={location}>{location}</p>
        </div>
        <div className="flex flex-wrap justify-center gap-2">
          <Button icon={<House />} nativeButton={false} render={<Link to="/" />}>Take me home</Button>
          <Button variant="outline" icon={<ArrowLeft />} onClick={onBack ?? (() => router.history.back())}>Go back</Button>
        </div>
      </div>
    </main>
  )
}
