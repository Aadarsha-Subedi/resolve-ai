import { lazy, Suspense, useState } from "react"
import { DatePicker, DateRangePicker, type IsoRange } from "@/components/patterns/date-picker"
import { ErrorScreen } from "@/components/patterns/error-screen"
import { Markdown } from "@/components/patterns/markdown"
import { NotFoundScreen } from "@/components/patterns/not-found-screen"
import { PageLoading } from "@/components/patterns/page-loading"
import { Restricted } from "@/components/patterns/restricted"
import { SettingGroup, SettingRow } from "@/components/patterns/setting-row"
import { ShortcutsList } from "@/components/patterns/shortcuts-menu"
import { StatCard } from "@/components/patterns/stat-card"
import { VolumeChart, type VolumeBucket } from "@/components/patterns/volume-chart"
import { Button } from "@/components/ui/button"
import type { Article } from "@/features/knowledge/api"
import { Switch } from "@/components/ui/switch"
import { EmptyState, ErrorPanel } from "@/features/app/page-states"
import { ArrowsClockwise, Pulse, Trash, Tray } from "@/icons"
import { ApiError } from "@/lib/api"
import { Section, Specimen } from "../section"

const GraphView = lazy(() => import("@/features/knowledge/knowledge-graph").then((m) => ({ default: m.GraphView })))
const GRAPH_CATEGORIES = [{ id: "c1", name: "Billing", slug: "billing" }, { id: "c2", name: "Technical", slug: "technical" }, { id: "c3", name: "Getting started", slug: "getting-started" }]
const graphArticle = (id: string, title: string, status: "draft" | "published" | "archived", categories: typeof GRAPH_CATEGORIES): Article => ({ id, title, status, categories, size_bytes: 1200, created_by: null, updated_by: null, created_at: "2026-03-01T00:00:00Z", updated_at: "2026-03-02T00:00:00Z", published_at: null })
const GRAPH_ARTICLES: Article[] = [
  graphArticle("a1", "Refund policy", "published", [GRAPH_CATEGORIES[0]]),
  graphArticle("a2", "Reading your invoice", "published", [GRAPH_CATEGORIES[0], GRAPH_CATEGORIES[2]]),
  graphArticle("a3", "Resetting a password", "published", [GRAPH_CATEGORIES[1], GRAPH_CATEGORIES[2]]),
  graphArticle("a4", "API rate limits", "draft", [GRAPH_CATEGORIES[1]]),
  graphArticle("a5", "Old pricing FAQ", "archived", []),
]

const BUCKETS: VolumeBucket[] = Array.from({ length: 14 }, (_, i) => {
  const day = String(i + 1).padStart(2, "0")
  return { start: `2026-03-${day}`, end: `2026-03-${day}`, created: [3, 5, 2, 0, 0, 6, 4, 7, 5, 3, 0, 1, 4, 6][i], resolved: [1, 2, 4, 0, 0, 3, 5, 4, 6, 3, 0, 2, 2, 5][i] }
})

const MD = "## Resetting a password\n\n1. Open **Settings** then *Security*.\n2. Choose *Reset password*.\n\n> Raw HTML such as <script>alert(1)</script> is never run.\n\n`code` and [links](https://example.com) work."

/** Patterns added with the authenticated screens. Sample data is fake. */
export function AppPatterns() {
  const [day, setDay] = useState<string | undefined>("2026-03-12")
  const [range, setRange] = useState<IsoRange>({ from: "2026-03-03", to: "2026-03-09" })
  return (
    <Section id="app-patterns" title="Screen patterns" intro="Pieces the signed-in screens share: permission gates that explain themselves, the shortcuts list, the volume chart and rendered Markdown.">
      <div className="grid gap-10 lg:grid-cols-2">
        <Specimen title="Restricted action" note="Hover or focus the disabled button: the reason appears in a tooltip, nothing is written under it.">
          <div className="flex flex-wrap gap-3">
            <Restricted reason="Only the workspace owner can do this.">
              <Button variant="destructive" icon={<Trash />}>Delete workspace</Button>
            </Restricted>
            <Restricted reason={null}>
              <Button variant="outline" icon={<ArrowsClockwise />}>Allowed action</Button>
            </Restricted>
          </div>
        </Specimen>
        <Specimen title="Shortcuts menu" note="Opened with ?, or from the search palette.">
          <div className="max-w-sm rounded-lg border p-3"><ShortcutsList /></div>
        </Specimen>
        <Specimen title="Volume chart" note="Created and resolved per day. Paired bars, legend, hover and keyboard tooltip, table view.">
          <VolumeChart buckets={BUCKETS} granularity="day" />
        </Specimen>
        <Specimen title="Markdown" note="Sanitised; used for knowledge articles.">
          <div className="rounded-lg border p-4"><Markdown>{MD}</Markdown></div>
        </Specimen>
        <Specimen title="Stat with neutral trend" note="Movement with no good or bad direction stays in muted ink.">
          <StatCard label="Created" icon={<Pulse />} value={42} trend={{ change: 6, percent: "17%", good: true, neutral: true, label: "vs the previous 30 days" }} className="max-w-xs" />
        </Specimen>
        <Specimen title="Date picker" note="Keyboard: arrows move days, Page Up/Down change month, Enter selects. Value is a YYYY-MM-DD string.">
          <div className="flex flex-wrap items-center gap-3">
            <DatePicker label="Due date" value={day} onChange={setDay} />
            <span className="text-xs text-muted-foreground tabular-nums">{day ?? "none"}</span>
          </div>
        </Specimen>
        <Specimen title="Date range picker" note="Used for ticket and audit date filters and the dashboard's custom range.">
          <div className="flex flex-wrap items-center gap-3">
            <DateRangePicker label="Created between" value={range} onChange={setRange} presets />
            <span className="text-xs text-muted-foreground tabular-nums">{range.from ? `${range.from} to ${range.to}` : "none"}</span>
          </div>
        </Specimen>
        <Specimen title="Knowledge graph" note="Categories to articles (React Flow, themed with the design tokens). Every article node holds a link, so Tab and Enter work; the controls zoom and fit. Sample data is fake.">
          <Suspense fallback={<div className="h-64 rounded-xl border bg-surface" />}>
            <GraphView workspaceId="preview" categories={GRAPH_CATEGORIES} articles={GRAPH_ARTICLES} total={GRAPH_ARTICLES.length} />
          </Suspense>
        </Specimen>
        <Specimen title="Setting rows" note="Title and description on the left, the control on the right, hairlines between rows; the control drops below the text on narrow screens. Danger zone goes last.">
          <SettingGroup id="preview-settings" title="General">
            <SettingRow title="Show the public portal" htmlFor="pv-portal" description="Customers can open tickets from the portal."><Switch id="pv-portal" defaultChecked /></SettingRow>
            <SettingRow danger title="Delete workspace" description="Everyone loses access immediately."><Button variant="destructive" icon={<Trash />}>Delete workspace</Button></SettingRow>
          </SettingGroup>
        </Specimen>
        <Specimen title="Router states" note="Full-page loading, crash (reload, no automatic retry) and not found. Set as the router's default pending, error and not-found components.">
          <div className="space-y-3">
            <div className="overflow-hidden rounded-xl border"><PageLoading className="min-h-64 py-6" /></div>
            <div className="overflow-hidden rounded-xl border"><ErrorScreen error={new Error("preview")} className="min-h-64 py-6" /></div>
            <div className="overflow-hidden rounded-xl border"><NotFoundScreen path="/app/unknown" className="min-h-64 py-6" /></div>
          </div>
        </Specimen>
        <Specimen title="Error and empty blocks">
          <div className="space-y-3">
            <ErrorPanel error={new ApiError(0, "x", "network_error")} onRetry={() => {}} title="Tickets could not be loaded" />
            <EmptyState icon={Tray} title="Nothing here yet">What goes here, and how to start.</EmptyState>
          </div>
        </Specimen>
      </div>
    </Section>
  )
}
