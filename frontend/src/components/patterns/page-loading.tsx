import { Spinner } from "@/components/ui/spinner"
import { Command } from "@/icons"
import { cn } from "@/lib/utils"

/** Full-page loading frame (route code still arriving): the mark, a spinner and a short line of text. */
export function PageLoading({ className }: { className?: string }) {
  return (
    <main aria-busy="true" aria-label="Loading" className={cn("grid min-h-[min(100dvh,36rem)] place-items-center bg-background px-6", className)}>
      <div className="flex w-full max-w-md flex-col items-center gap-5">
        <span className="grid size-12 place-items-center rounded-xl bg-primary text-primary-foreground" aria-hidden>
          <Command weight="bold" className="size-7" />
        </span>
        <Spinner aria-hidden role="presentation" className="size-6 text-muted-foreground" />
        <p role="status" className="text-sm text-muted-foreground">Resolve AI is loading</p>
      </div>
    </main>
  )
}
