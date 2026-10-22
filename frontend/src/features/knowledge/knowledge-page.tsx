import { useNavigate } from '@tanstack/react-router'
import { formatDistanceToNowStrict } from 'date-fns'

import { DataTable, type DataColumn } from '@/components/patterns/data-table'
import { FilterBar } from '@/components/patterns/filter-bar'
import { PageHeader } from '@/components/patterns/page-header'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { EmptyState, ErrorPanel } from '@/features/app/page-states'
import { useWorkspace } from '@/features/app/workspace-context'
import { ARTICLE_PAGE_SIZE, useArticles, useCategories, type Article } from '@/features/knowledge/api'
import { FilesSection } from '@/features/knowledge/files-section'
import { NewContentDialog } from '@/features/knowledge/new-content-dialog'
import type { KnowledgeSearch } from '@/features/knowledge/search'
import { ArticleStatusBadge } from '@/features/knowledge/status-badge'
import { ARTICLE_STATUS_OPTIONS } from '@/features/knowledge/status-options'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { ArrowLeft, ArrowRight, CircleHalf, ListBullets, Notebook, Plus, Tag, TreeStructure } from '@/icons'
import { lazy, Suspense, useState } from 'react'

// The graph library is only loaded when the graph view opens.
const KnowledgeGraph = lazy(() => import('@/features/knowledge/knowledge-graph').then((m) => ({ default: m.KnowledgeGraph })))

const columns: DataColumn<Article>[] = [
  { id: 'title', header: 'Title', enableHiding: false, meta: { label: 'Title' }, cell: ({ row }) => <span className="truncate font-medium" title={row.original.title}>{row.original.title}</span> },
  { id: 'status', header: 'Status', cell: ({ row }) => <ArticleStatusBadge status={row.original.status} /> },
  { id: 'categories', header: 'Categories', cell: ({ row }) => <span className="truncate text-muted-foreground">{row.original.categories.map((c) => c.name).join(', ') || '—'}</span> },
  { id: 'updated', header: 'Updated', cell: ({ row }) => <span className="text-muted-foreground">{formatDistanceToNowStrict(new Date(row.original.updated_at), { addSuffix: true })}</span> },
]
const EMPTY: Article[] = []

function ArticlesView({ search }: { search: KnowledgeSearch }) {
  const { workspace } = useWorkspace()
  const navigate = useNavigate()
  const articles = useArticles(workspace.id, search)
  const update = (patch: Partial<KnowledgeSearch>) =>
    void navigate({ to: '.', search: ((prev: KnowledgeSearch) => ({ ...prev, ...patch, page: 'page' in patch ? patch.page : undefined })) as never, replace: true })
  const categories = useCategories(workspace.id, true)
  const categoryOptions = (categories.data ?? []).map((c) => ({ value: c.id, label: c.name }))
  const filtered = Boolean(search.title || search.status || search.category)
  const page = search.page ?? 1
  const count = articles.data?.meta.count ?? 0
  const to = Math.min(count, page * ARTICLE_PAGE_SIZE)

  const graph = search.view === 'graph'
  const viewToggle = (
    <ToggleGroup size="sm" spacing={1} value={[graph ? 'graph' : 'list']} onValueChange={(v) => v[0] && void navigate({ to: '.', search: (() => ({ view: v[0] === 'graph' ? 'graph' : undefined })) as never, replace: true })} aria-label="View">
      {([['list', 'Show as list', ListBullets], ['graph', 'Show as graph', TreeStructure]] as const).map(([value, text, Icon]) => (
        <Tooltip key={value}>
          <TooltipTrigger render={<ToggleGroupItem value={value} aria-label={text} className="w-7 px-0" />}><Icon /></TooltipTrigger>
          <TooltipContent>{text}</TooltipContent>
        </Tooltip>
      ))}
    </ToggleGroup>
  )

  if (graph) {
    return (
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm text-muted-foreground">Categories and the articles filed under them. Open an article from its node.</p>
          {viewToggle}
        </div>
        <Suspense fallback={<Skeleton className="h-[28rem] w-full" aria-busy="true" aria-label="Loading graph" />}>
          <KnowledgeGraph workspaceId={workspace.id} />
        </Suspense>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <FilterBar
        search={{ value: search.title ?? '', onCommit: (title) => update({ title }), placeholder: 'Search article titles' }}
        filters={[
          { id: 'status', kind: 'select', label: 'Status', icon: CircleHalf, options: ARTICLE_STATUS_OPTIONS, value: search.status, onChange: (v) => update({ status: v as KnowledgeSearch['status'] }) },
          { id: 'category', kind: 'select', label: 'Category', icon: Tag, options: categoryOptions, value: search.category, onChange: (category) => update({ category }) },
        ]}
        onClearAll={() => void navigate({ to: '.', search: {} as never, replace: true })}
        trailing={<span className="ml-auto">{viewToggle}</span>}
      />
      {articles.error ? (
        <ErrorPanel error={articles.error} onRetry={() => void articles.refetch()} title="Articles could not be loaded" />
      ) : (
        <DataTable
          columns={columns}
          data={articles.data?.items ?? EMPTY}
          getRowId={(a) => a.id}
          caption="Knowledge base articles"
          loading={articles.isPending}
          onRowClick={(a) => void navigate({ to: `/app/${workspace.id}/knowledge/${a.id}` as never })}
          empty={
            <EmptyState icon={Notebook} title={filtered ? 'No articles match these filters' : 'No articles yet'}>
              {filtered ? 'Try fewer filters or a different search.' : 'Use New to write down answers your team gives again and again.'}
            </EmptyState>
          }
          footer={
            count > 0 ? (
              <div className="flex items-center justify-between gap-3 text-sm text-muted-foreground">
                <span className="tabular-nums">{(page - 1) * ARTICLE_PAGE_SIZE + 1}–{to} of {count}</span>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" icon={<ArrowLeft />} disabled={page <= 1} onClick={() => update({ page: page - 1 || undefined })}>Previous</Button>
                  <Button variant="outline" size="sm" iconEnd={<ArrowRight />} disabled={to >= count} onClick={() => update({ page: page + 1 })}>Next</Button>
                </div>
              </div>
            ) : null
          }
        />
      )}
      {!search.status && <FilesSection workspaceId={workspace.id} category={search.category} filename={search.title} />}
    </div>
  )
}

export function KnowledgePage({ search }: { search: KnowledgeSearch }) {
  useDocumentTitle('Articles · ResolveAI')
  const { workspace } = useWorkspace()
  const [adding, setAdding] = useState(false)
  return (
    <div className="space-y-5">
      <PageHeader title="Articles" description="Articles and files your team (and later, AI drafts) can rely on, each filed under a category." actions={<Button icon={<Plus />} onClick={() => setAdding(true)}>New</Button>} />
      <ArticlesView search={search} />
      <NewContentDialog workspaceId={workspace.id} open={adding} onOpenChange={setAdding} />
    </div>
  )
}
