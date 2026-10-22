import type { Article, ArticleStatus, Category, Upload } from '@/features/knowledge/api'

export const UNCATEGORIZED_ID = '__uncategorized'

export type CategoryNodeData = { kind: 'category'; name: string; count: number; [key: string]: unknown }
/** `workspaceId` is added by the view, so a node can link to its article. */
export type ArticleNodeData = { kind: 'article'; id: string; title: string; status: ArticleStatus; workspaceId?: string; [key: string]: unknown }
export type FileNodeData = { kind: 'file'; filename: string; contentType: string; [key: string]: unknown }
export type GraphNode = { id: string; type: 'category' | 'article' | 'file'; position: { x: number; y: number }; data: CategoryNodeData | ArticleNodeData | FileNodeData }
export type GraphEdge = { id: string; source: string; target: string }

export const COLUMN_GAP = 340
export const ROW_GAP = 64

/**
 * Category graph, drawn as two columns: categories on the left, articles on the right, one edge per membership
 * (an article in two categories has two edges). Files hang off their one category. Articles and files with no category hang
 * off an "Uncategorized" node. Items are ordered by their first category so edges rarely cross, and each category sits at the middle of its articles.
 * Article-to-article links are not part of v1.
 */
export function buildKnowledgeGraph(categories: Category[], articles: Article[], uploads: Upload[] = []): { nodes: GraphNode[]; edges: GraphEdge[] } {
  const order = new Map(categories.map((c, i) => [c.id, i]))
  const hasUncategorized = articles.some((a) => a.categories.length === 0) || uploads.some((u) => !u.category)
  const groups: { id: string; name: string }[] = [...categories.map((c) => ({ id: c.id, name: c.name })), ...(hasUncategorized ? [{ id: UNCATEGORIZED_ID, name: 'Uncategorized' }] : [])]
  type Item = { id: string; type: 'article' | 'file'; label: string; categoryIds: string[]; data: ArticleNodeData | FileNodeData }
  const items: Item[] = [
    ...articles.map((a): Item => ({ id: `a:${a.id}`, type: 'article', label: a.title, categoryIds: a.categories.map((c) => c.id), data: { kind: 'article', id: a.id, title: a.title, status: a.status } })),
    ...uploads.map((u): Item => ({ id: `f:${u.id}`, type: 'file', label: u.filename, categoryIds: u.category ? [u.category.id] : [], data: { kind: 'file', filename: u.filename, contentType: u.content_type } })),
  ]
  const rank = (item: Item) => (item.categoryIds.length === 0 ? categories.length : Math.min(...item.categoryIds.map((id) => order.get(id) ?? categories.length)))
  const sorted = items.sort((x, y) => rank(x) - rank(y) || x.label.localeCompare(y.label))

  const itemY = new Map(sorted.map((item, i) => [item.id, i * ROW_GAP]))
  const nodes: GraphNode[] = []
  const edges: GraphEdge[] = []
  const members = new Map<string, number[]>(groups.map((g) => [g.id, []]))

  for (const item of sorted) {
    nodes.push({ id: item.id, type: item.type, position: { x: COLUMN_GAP, y: itemY.get(item.id)! }, data: item.data })
    const ids = item.categoryIds.length ? item.categoryIds : [UNCATEGORIZED_ID]
    for (const id of ids) {
      if (!members.has(id)) continue // a category the list did not return
      members.get(id)!.push(itemY.get(item.id)!)
      edges.push({ id: `e:${id}:${item.id.slice(2)}`, source: `c:${id}`, target: item.id })
    }
  }

  // Each category starts at the middle of its items; categories that would overlap are pushed down.
  const placed = groups
    .map((group) => ({ group, ys: members.get(group.id)!, y: 0 }))
    .map((p) => ({ ...p, y: p.ys.length ? p.ys.reduce((x, y) => x + y, 0) / p.ys.length : Infinity }))
    .sort((p, q) => p.y - q.y)
  let nextFree = 0
  for (const p of placed) {
    const y = Number.isFinite(p.y) ? Math.max(p.y, nextFree) : nextFree
    nextFree = y + ROW_GAP
    nodes.push({ id: `c:${p.group.id}`, type: 'category', position: { x: 0, y }, data: { kind: 'category', name: p.group.name, count: p.ys.length } })
  }
  return { nodes, edges }
}
