import { Link, useNavigate } from '@tanstack/react-router'
import { formatDistanceToNowStrict } from 'date-fns'
import type { ReactNode } from 'react'

import { PageHeader } from '@/components/patterns/page-header'
import { PriorityLabel, SoftBadge, TicketStatusBadge } from '@/components/patterns/ticket-meta'
import { StatCard, type StatTrend } from '@/components/patterns/stat-card'
import { VolumeChart } from '@/components/patterns/volume-chart'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { EmptyState, ErrorPanel } from '@/features/app/page-states'
import { useWorkspace } from '@/features/app/workspace-context'
import { useDashboard, type Dashboard } from '@/features/dashboard/api'
import { DateRangePicker } from '@/components/patterns/date-picker'
import { MAX_CUSTOM_DAYS, PERIODS, type DashboardSearch } from '@/features/dashboard/search'
import { toast } from 'sonner'
import { describeEvent } from '@/features/tickets/ticket-events'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { CheckCircle, Clock, Flame, Pulse, TrayArrowDown } from '@/icons'
import type { TicketEvent } from '@/lib/types'

function trend(
  current: number,
  previous: number,
  days: number,
  good: boolean | 'neutral',
): StatTrend {
  const change = current - previous
  return {
    change,
    percent:
      previous === 0
        ? current === 0
          ? '0%'
          : 'new'
        : `${Math.round((Math.abs(change) / previous) * 100)}%`,
    good: good === 'neutral' ? true : good,
    neutral: good === 'neutral',
    label: `vs the previous ${days} days`,
  }
}

function Summary({ data, loading }: { data?: Dashboard; loading: boolean }) {
  const s = data?.summary
  const days = data?.period.days ?? 30
  return (
    <section aria-label="Summary" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
      <StatCard
        label="Active tickets"
        icon={<TrayArrowDown />}
        loading={loading}
        value={s?.active}
      />
      <StatCard label="Urgent" icon={<Flame />} loading={loading} value={s?.urgent} />
      <StatCard
        label="Waiting for reply"
        icon={<Clock />}
        loading={loading}
        value={s?.waiting_for_reply}
      />
      <StatCard
        label="Created"
        icon={<Pulse />}
        loading={loading}
        value={s?.created.current}
        trend={s ? trend(s.created.current, s.created.previous, days, 'neutral') : undefined}
      />
      <StatCard
        label="Resolved"
        icon={<CheckCircle />}
        loading={loading}
        value={s?.resolved.current}
        trend={
          s
            ? trend(
                s.resolved.current,
                s.resolved.previous,
                days,
                s.resolved.current >= s.resolved.previous,
              )
            : undefined
        }
      />
    </section>
  )
}

function Panel({
  title,
  action,
  children,
}: {
  title: string
  action?: ReactNode
  children: ReactNode
}) {
  return (
    <section className="flex flex-col gap-3 rounded-xl border p-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  )
}

function ListSkeleton() {
  return (
    <div className="space-y-2" aria-busy="true" aria-label="Loading">
      {Array.from({ length: 4 }, (_, i) => (
        <Skeleton key={i} className="h-9 w-full" />
      ))}
    </div>
  )
}

export function DashboardPage({ search }: { search: DashboardSearch }) {
  useDocumentTitle('Dashboard · ResolveAI')
  const { workspace } = useWorkspace()
  const navigate = useNavigate()
  const custom = search.from && search.to ? { from: search.from, to: search.to } : null
  const tab = custom ? 'custom' : (search.period ?? '30d')
  const dashboard = useDashboard(workspace.id, custom ?? { period: search.period ?? '30d' })
  const data = dashboard.data
  const to = (id: string) => `/app/${workspace.id}/tickets/${id}` as never

  return (
    <div className="space-y-5">
      <PageHeader
        title="Dashboard"
        description={
          data
            ? `${workspace.name} · ${data.period.from} to ${data.period.to} (${data.period.tz})`
            : workspace.name
        }
        actions={
          <>
            {tab === 'custom' && (
              <DateRangePicker
                label="Custom range"
                value={{ from: search.from, to: search.to }}
                onChange={(r) => {
                  if (!r.from || !r.to)
                    return void navigate({ to: '.', search: {} as never, replace: true })
                  const days =
                    Math.round(
                      (new Date(r.to).getTime() - new Date(r.from).getTime()) / 86_400_000,
                    ) + 1
                  if (days > MAX_CUSTOM_DAYS)
                    return void toast.error(`Pick at most ${MAX_CUSTOM_DAYS} days.`)
                  void navigate({
                    to: '.',
                    search: { from: r.from, to: r.to } as never,
                    replace: true,
                  })
                }}
              />
            )}
            <Tabs
              value={tab}
              onValueChange={(v) => {
                if (v === 'custom') {
                  // Start from the last 30 days; the picker then adjusts it.
                  const end = new Date()
                  const start = new Date(end.getTime() - 29 * 86_400_000)
                  const iso = (d: Date) =>
                    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
                  return void navigate({
                    to: '.',
                    search: { from: iso(start), to: iso(end) } as never,
                    replace: true,
                  })
                }
                void navigate({
                  to: '.',
                  search: (v === '30d' ? {} : { period: v }) as never,
                  replace: true,
                })
              }}
            >
              <TabsList aria-label="Period">
                {PERIODS.map((p) => (
                  <TabsTrigger key={p.value} value={p.value}>
                    {p.label}
                  </TabsTrigger>
                ))}
                <TabsTrigger value="custom">Custom</TabsTrigger>
              </TabsList>
            </Tabs>
          </>
        }
      />
      {dashboard.error ? (
        <ErrorPanel
          error={dashboard.error}
          onRetry={() => void dashboard.refetch()}
          title="The dashboard could not be loaded"
        />
      ) : (
        <>
          <Summary data={data} loading={dashboard.isPending} />
          <div className="grid gap-4 lg:grid-cols-2">
            <Panel title="Tickets over time">
              {data ? (
                <VolumeChart buckets={data.volume.buckets} granularity={data.volume.granularity} />
              ) : (
                <Skeleton className="h-52 w-full" />
              )}
            </Panel>
            <Panel title="Recent activity">
              {!data ? (
                <ListSkeleton />
              ) : data.activity.items.length === 0 ? (
                <EmptyState icon={Pulse} title="No activity yet">
                  Changes to tickets show up here.
                </EmptyState>
              ) : (
                <ul className="divide-y">
                  {data.activity.items.map((a) => (
                    <li key={a.id}>
                      <Link
                        to={to(a.ticket.id)}
                        className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5 rounded-md py-2 outline-none hover:bg-muted/60 focus-visible:ring-3 focus-visible:ring-ring/50"
                      >
                        <span className="text-sm">
                          {describeEvent({
                            ...a,
                            actor: a.actor?.id ?? null,
                            metadata: {},
                          } as unknown as TicketEvent)}
                        </span>
                        <span className="min-w-0 flex-1 truncate text-xs text-muted-foreground">
                          #{a.ticket.number} {a.ticket.subject}
                          {a.actor ? ` · ${a.actor.name}` : ''}
                        </span>
                        <span className="text-xs text-muted-foreground" title={a.created_at}>
                          {formatDistanceToNowStrict(new Date(a.created_at), { addSuffix: true })}
                        </span>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </Panel>
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <Panel
              title="Waiting for a reply"
              action={
                data && (
                  <span className="text-xs tabular-nums text-muted-foreground">
                    {data.waiting.total} in total
                  </span>
                )
              }
            >
              {!data ? (
                <ListSkeleton />
              ) : data.waiting.items.length === 0 ? (
                <EmptyState icon={CheckCircle} title="Nobody is waiting">
                  Every active ticket has an answer.
                </EmptyState>
              ) : (
                <ul className="divide-y">
                  {data.waiting.items.map((t) => (
                    <li key={t.id}>
                      <Link
                        to={to(t.id)}
                        className="flex items-center gap-3 rounded-md py-2 outline-none hover:bg-muted/60 focus-visible:ring-3 focus-visible:ring-ring/50"
                      >
                        <span className="tabular-nums text-xs text-muted-foreground">
                          #{t.number}
                        </span>
                        <span className="min-w-0 flex-1 truncate text-sm">{t.subject}</span>
                        <PriorityLabel priority={t.priority} className="text-xs" />
                        <span className="text-xs text-muted-foreground" title={t.waiting_since}>
                          {formatDistanceToNowStrict(new Date(t.waiting_since))}
                        </span>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </Panel>
            <Panel title="Recently updated">
              {!data ? (
                <ListSkeleton />
              ) : data.recent_tickets.items.length === 0 ? (
                <EmptyState icon={TrayArrowDown} title="No tickets yet">
                  New tickets from email and the portal appear here.
                </EmptyState>
              ) : (
                <ul className="divide-y">
                  {data.recent_tickets.items.map((t) => (
                    <li key={t.id}>
                      <Link
                        to={to(t.id)}
                        className="flex items-center gap-3 rounded-md py-2 outline-none hover:bg-muted/60 focus-visible:ring-3 focus-visible:ring-ring/50"
                      >
                        <span className="tabular-nums text-xs text-muted-foreground">
                          #{t.number}
                        </span>
                        <span className="min-w-0 flex-1 truncate text-sm">{t.subject}</span>
                        {t.waiting_for_reply && (
                          <SoftBadge tone="warning" icon={Clock}>
                            Waiting
                          </SoftBadge>
                        )}
                        <TicketStatusBadge status={t.status} />
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </Panel>
          </div>
        </>
      )}
    </div>
  )
}
