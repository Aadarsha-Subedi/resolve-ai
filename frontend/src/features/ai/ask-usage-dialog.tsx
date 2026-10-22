import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { useLlmSettings } from '@/features/ai/api'
import { ErrorPanel, LinesSkeleton } from '@/features/app/page-states'
import { X } from '@/icons'
import { cn } from '@/lib/utils'

const resetTime = (iso: string) =>
  new Date(iso).toLocaleString(undefined, { weekday: 'short', hour: 'numeric', minute: '2-digit' })

/** Today's Resolve AI searches for this user in this workspace, and when the count resets. Mounted only while open. */
export function AskUsageDialog({
  workspaceId,
  open,
  onOpenChange,
}: {
  workspaceId: string
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const settings = useLlmSettings(workspaceId)
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Usage</DialogTitle>
          <DialogDescription>Each question uses up to 2 searches.</DialogDescription>
        </DialogHeader>
        {settings.isPending ? (
          <LinesSkeleton rows={2} />
        ) : settings.error ? (
          <ErrorPanel
            error={settings.error}
            onRetry={() => void settings.refetch()}
            title="Usage could not be loaded"
          />
        ) : settings.data.mode === 'own_key' ? (
          <p className="text-sm">
            You are using your own API key. Searches are not counted here; your provider sets the
            limits.
          </p>
        ) : (
          (() => {
            const { used_today: used, limit, remaining, resets_at } = settings.data.usage
            const pct = limit > 0 ? Math.min(100, Math.round((used / limit) * 100)) : 0
            const low = remaining <= Math.ceil(limit * 0.1)
            return (
              <div className="space-y-2">
                <p className="text-sm tabular-nums">
                  <span className="font-medium">
                    {used} of {limit}
                  </span>{' '}
                  searches used today · {remaining} left
                </p>
                <div
                  role="progressbar"
                  aria-label="Searches used today"
                  aria-valuemin={0}
                  aria-valuemax={limit}
                  aria-valuenow={used}
                  className="h-1.5 overflow-hidden rounded-full bg-muted"
                >
                  <div
                    className={cn('h-full rounded-full', low ? 'bg-warning' : 'bg-primary')}
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <p className="text-sm text-muted-foreground">Resets {resetTime(resets_at)}.</p>
              </div>
            )
          })()
        )}
        <DialogFooter>
          <Button type="button" variant="outline" icon={<X />} onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
