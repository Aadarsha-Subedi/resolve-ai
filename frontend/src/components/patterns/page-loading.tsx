import { Skeleton } from "@/components/ui/skeleton"
import { Command } from "@/icons"
import { cn } from "@/lib/utils"

/** Full-page loading frame (route code still arriving): the mark and the outline of a page, nothing that moves except the skeleton shimmer. */
export function PageLoading({ className }: { className?: string }) {
  return (
    <main aria-busy="true" aria-label="Loading" className={cn("grid min-h-[min(100dvh,36rem)] place-items-center bg-background px-6", className)}>
      <div className="flex w-full max-w-md flex-col items-center gap-6">
        <span className="grid size-12 place-items-center rounded-xl bg-primary text-primary-foreground" aria-hidden>
          <Command weight="bold" className="size-7" />
        </span>
        <div className="w-full space-y-3">
          <Skeleton className="mx-auto h-6 w-48" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
          <Skeleton className="h-24 w-full" />
        </div>
        <span className="sr-only" role="status">Loading</span>
      </div>
    </main>
  )
}
