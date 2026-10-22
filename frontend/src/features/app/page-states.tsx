import type { ReactNode } from 'react'

import { Button } from '@/components/ui/button'
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle, EmptyContent } from '@/components/ui/empty'
import { Skeleton } from '@/components/ui/skeleton'
import { ArrowClockwise, WarningCircle } from '@/icons'
import type { PhosphorIcon } from '@/icons'
import { ApiError, errorMessage } from '@/lib/api'

/** Inline failure for one block of a page. "Try again" is a user action; nothing retries by itself. */
export function ErrorPanel({ error, onRetry, title = 'This could not be loaded' }: { error: unknown; onRetry?: () => void; title?: string }) {
  const network = error instanceof ApiError && error.code === 'network_error'
  const forbidden = error instanceof ApiError && (error.status === 403 || error.status === 404)
  return (
    <div role="alert" className="flex flex-col items-start gap-3 rounded-xl border bg-card p-4">
      <div className="flex items-start gap-2">
        <WarningCircle weight="fill" className="mt-0.5 size-5 shrink-0 text-warning" aria-hidden />
        <div className="space-y-0.5">
          <p className="text-sm font-medium">{forbidden ? 'You do not have access to this' : title}</p>
          <p className="text-sm text-muted-foreground">{network ? 'Check your connection, then try again.' : errorMessage(error)}</p>
        </div>
      </div>
      {onRetry && <Button variant="outline" size="sm" icon={<ArrowClockwise />} onClick={onRetry}>Try again</Button>}
    </div>
  )
}

/** Empty list that says what goes here and, when the viewer can, how to start. */
export function EmptyState({ icon: Icon, title, children, action }: { icon: PhosphorIcon; title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <Empty className="py-10">
      <EmptyHeader>
        <EmptyMedia variant="icon"><Icon /></EmptyMedia>
        <EmptyTitle>{title}</EmptyTitle>
        {children && <EmptyDescription>{children}</EmptyDescription>}
      </EmptyHeader>
      {action && <EmptyContent>{action}</EmptyContent>}
    </Empty>
  )
}

/** A stack of text-line skeletons for blocks that are not tables. */
export function LinesSkeleton({ rows = 4, className }: { rows?: number; className?: string }) {
  return (
    <div className={className ?? 'space-y-3'} aria-busy="true" aria-label="Loading">
      {Array.from({ length: rows }, (_, i) => <Skeleton key={i} className="h-5 w-full" style={{ maxWidth: `${92 - i * 11}%` }} />)}
    </div>
  )
}
