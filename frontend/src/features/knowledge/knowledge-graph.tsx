import '@xyflow/react/dist/style.css'

import { Link } from '@tanstack/react-router'
import { Background, Controls, Handle, Position, ReactFlow, type Edge, type Node, type NodeProps, type NodeTypes } from '@xyflow/react'
import { useMemo } from 'react'

import { EmptyState, ErrorPanel } from '@/features/app/page-states'
import { Skeleton } from '@/components/ui/skeleton'
import { GRAPH_ARTICLE_LIMIT, useArticleGraph, useCategories, useUploads, type Article, type Category, type Upload } from '@/features/knowledge/api'
import { buildKnowledgeGraph, type ArticleNodeData, type CategoryNodeData, type FileNodeData } from '@/features/knowledge/graph-layout'
import { ArticleStatusBadge } from '@/features/knowledge/status-badge'
import { useTheme } from '@/hooks/use-theme'
import { FilePdf, FileText, Notebook, Tag, TreeStructure } from '@/icons'

const handleClass = '!size-1.5 !min-h-0 !min-w-0 !border-0 !bg-border'

function CategoryNode({ data }: NodeProps<Node<CategoryNodeData>>) {
  return (
    <div className="flex w-56 items-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground shadow-[inset_0_1px_0_oklch(1_0_0/0.35),0_1px_2px_oklch(0_0_0/0.12)]">
      <Tag className="size-4 shrink-0" weight="bold" aria-hidden />
      <span className="min-w-0 flex-1 truncate" title={data.name}>{data.name}</span>
      <span className="text-xs tabular-nums opacity-70" aria-label={`${data.count} ${data.count === 1 ? 'article' : 'articles'}`}>{data.count}</span>
      <Handle type="source" position={Position.Right} className={handleClass} isConnectable={false} />
    </div>
  )
}

function ArticleNode({ data }: NodeProps<Node<ArticleNodeData>>) {
  return (
    <div className="relative flex w-64 items-center gap-2 rounded-lg border bg-card px-3 py-2 text-sm text-card-foreground shadow-xs focus-within:ring-3 focus-within:ring-ring/50 hover:bg-muted/60">
      <Handle type="target" position={Position.Left} className={handleClass} isConnectable={false} />
      <Notebook className="size-4 shrink-0 text-muted-foreground" aria-hidden />
      <Link to={`/app/${data.workspaceId}/knowledge/${data.id}` as never} className="min-w-0 flex-1 truncate font-medium outline-none after:absolute after:inset-0 after:rounded-lg" title={data.title}>{data.title}</Link>
      <ArticleStatusBadge status={data.status} />
    </div>
  )
}


function FileNode({ data }: NodeProps<Node<FileNodeData>>) {
  const Icon = data.contentType === 'application/pdf' ? FilePdf : FileText
  return (
    <div className="flex w-64 items-center gap-2 rounded-lg border border-dashed bg-card px-3 py-2 text-sm text-card-foreground">
      <Handle type="target" position={Position.Left} className={handleClass} isConnectable={false} />
      <Icon className="size-4 shrink-0 text-muted-foreground" aria-hidden />
      <span className="min-w-0 flex-1 truncate" title={data.filename}>{data.filename}</span>
      <span className="text-xs text-muted-foreground">File</span>
    </div>
  )
}

const nodeTypes: NodeTypes = { category: CategoryNode, article: ArticleNode, file: FileNode }

/**
 * Category graph of the knowledge base (articles and files) (React Flow). Every article node holds a real link, so Tab walks the
 * articles and Enter opens one; the Controls buttons zoom and fit the view. Nodes are not draggable or connectable:
 * the graph is a map, not an editor. The list view stays the place to filter and search.
 */
export function KnowledgeGraph({ workspaceId }: { workspaceId: string }) {
  const articles = useArticleGraph(workspaceId, true)
  const categories = useCategories(workspaceId, true)
  const files = useUploads(workspaceId, {})
  const error = articles.error ?? categories.error ?? files.error
  if (error) return <ErrorPanel error={error} onRetry={() => { void articles.refetch(); void categories.refetch(); void files.refetch() }} title="The graph could not be loaded" />
  if (!articles.data || !categories.data || !files.data) return <Skeleton className="h-[28rem] w-full" aria-busy="true" aria-label="Loading graph" />
  return <GraphView workspaceId={workspaceId} categories={categories.data} articles={articles.data.items} uploads={files.data} total={articles.data.meta.count} />
}

/** The drawing itself, from plain data (also used by the design preview). */
export function GraphView({ workspaceId, categories, articles, uploads = [], total }: { workspaceId: string; categories: Category[]; articles: Article[]; uploads?: Upload[]; total: number }) {
  const { resolved } = useTheme()
  const graph = useMemo(() => {
    const built = buildKnowledgeGraph(categories, articles, uploads)
    const nodes: Node[] = built.nodes.map((n) => ({ ...n, data: { ...n.data, workspaceId }, focusable: false, draggable: false, connectable: false, selectable: false }))
    const edges: Edge[] = built.edges.map((e) => ({ ...e, type: 'smoothstep', focusable: false, selectable: false }))
    return { nodes, edges }
  }, [categories, articles, uploads, workspaceId])

  if (graph.nodes.length === 0) return <EmptyState icon={TreeStructure} title="Nothing to draw yet">Add an article or a file under a category to see it here.</EmptyState>
  return (
    <div className="space-y-2">
      <div className="h-[min(36rem,65vh)] overflow-hidden rounded-xl border bg-surface" role="group" aria-label="Knowledge graph: categories and the articles filed under them. Use Tab to move between articles and Enter to open one.">
        <ReactFlow
          className="resolve-flow"
          nodes={graph.nodes}
          edges={graph.edges}
          nodeTypes={nodeTypes}
          colorMode={resolved}
          fitView
          fitViewOptions={{ padding: 0.15 }}
          minZoom={0.3}
          maxZoom={1.5}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable={false}
          proOptions={{ hideAttribution: true }}
          aria-label="Knowledge graph"
        >
          <Background gap={20} size={1} />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
      {total > GRAPH_ARTICLE_LIMIT && <p className="text-xs text-muted-foreground">Showing the {GRAPH_ARTICLE_LIMIT} most recently updated of {total} articles. Use the list to find the rest.</p>}
    </div>
  )
}
