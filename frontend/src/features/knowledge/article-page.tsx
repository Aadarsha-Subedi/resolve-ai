import { Link, useNavigate } from '@tanstack/react-router'
import { useState } from 'react'
import { toast } from 'sonner'

import { ConfirmDialog } from '@/components/patterns/confirm-dialog'
import { Markdown } from '@/components/patterns/markdown'
import { Restricted } from '@/components/patterns/restricted'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ErrorPanel } from '@/features/app/page-states'
import { useWorkspace } from '@/features/app/workspace-context'
import { useArticle, useArticleStatus, useCategories, useCreateArticle, useDeleteArticle, useUpdateArticle, type Article } from '@/features/knowledge/api'
import { ArticleEditor, type EditorValue } from '@/features/knowledge/article-editor'
import { ArticleStatusBadge } from '@/features/knowledge/status-badge'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { Archive, ArrowLeft, CloudArrowUp, FloppyDisk, PencilSimple, Trash } from '@/icons'
import { ApiError, errorMessage, fieldError } from '@/lib/api'
import { formatDateTime } from '@/lib/format'

const toValue = (article?: Article): EditorValue => ({ title: article?.title ?? '', content: article?.content ?? '', categories: article?.categories ?? [] })

function BackLink({ workspaceId }: { workspaceId: string }) {
  return <Button variant="ghost" size="sm" icon={<ArrowLeft />} nativeButton={false} render={<Link to={`/app/${workspaceId}/knowledge` as never} />}>Articles</Button>
}

/** /knowledge/new: an empty editor. Saving creates a draft and opens it. */
export function NewArticlePage({ initialCategory }: { initialCategory?: string }) {
  useDocumentTitle('New article · ResolveAI')
  const { workspace } = useWorkspace()
  const navigate = useNavigate()
  const create = useCreateArticle(workspace.id)
  const [value, setValue] = useState<EditorValue>(toValue())
  // The category picked in the New dialog is filed on the draft once its name is known.
  const categories = useCategories(workspace.id, !!initialCategory)
  const [seeded, setSeeded] = useState(false)
  const preselected = initialCategory ? categories.data?.find((c) => c.id === initialCategory) : undefined
  if (preselected && !seeded) {
    setSeeded(true)
    setValue((current) => ({ ...current, categories: [preselected] }))
  }
  const save = () =>
    create.mutate(
      { title: value.title.trim(), content: value.content, category_ids: value.categories.map((c) => c.id) },
      {
        onSuccess: (article) => {
          toast.success('Draft saved.')
          void navigate({ to: `/app/${workspace.id}/knowledge/${article.id}` as never })
        },
        onError: (e) => {
          if (!fieldError(e, 'title') && !fieldError(e, 'content')) toast.error(errorMessage(e))
        },
      },
    )
  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <BackLink workspaceId={workspace.id} />
      <h1 className="font-display text-2xl font-semibold tracking-tight">New article</h1>
      <ArticleEditor workspaceId={workspace.id} value={value} onChange={setValue} error={create.error} />
      <Button icon={<FloppyDisk />} loading={create.isPending} disabled={!value.title.trim()} onClick={save}>Save draft</Button>
    </div>
  )
}

function EditArticle({ article, onDone }: { article: Article; onDone: () => void }) {
  const { workspace } = useWorkspace()
  const update = useUpdateArticle(workspace.id, article.id)
  const [value, setValue] = useState<EditorValue>(toValue(article))
  const save = () => {
    const changes: Parameters<typeof update.mutate>[0] = {}
    if (value.title.trim() !== article.title) changes.title = value.title.trim()
    if (value.content !== (article.content ?? '')) changes.content = value.content
    const before = article.categories.map((c) => c.id).sort().join()
    const after = value.categories.map((c) => c.id).sort().join()
    if (before !== after) changes.category_ids = value.categories.map((c) => c.id)
    if (Object.keys(changes).length === 0) return onDone()
    update.mutate(changes, {
      onSuccess: () => {
        toast.success('Article saved.')
        onDone()
      },
      onError: (e) => {
        if (!fieldError(e, 'title') && !fieldError(e, 'content')) toast.error(errorMessage(e))
      },
    })
  }
  return (
    <div className="space-y-5">
      <ArticleEditor workspaceId={workspace.id} value={value} onChange={setValue} error={update.error} />
      <div className="flex gap-2">
        <Button icon={<FloppyDisk />} loading={update.isPending} disabled={!value.title.trim()} onClick={save}>Save changes</Button>
        <Button variant="outline" onClick={onDone}>Cancel</Button>
      </div>
    </div>
  )
}

export function ArticlePage({ articleId }: { articleId: string }) {
  const { workspace } = useWorkspace()
  const navigate = useNavigate()
  const article = useArticle(workspace.id, articleId)
  const status = useArticleStatus(workspace.id, articleId)
  const remove = useDeleteArticle(workspace.id, articleId)
  const [editing, setEditing] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  useDocumentTitle(article.data ? `${article.data.title} · ResolveAI` : 'Article · ResolveAI')

  if (article.isPending) return <div className="mx-auto max-w-3xl space-y-4" aria-busy="true" aria-label="Loading article"><Skeleton className="h-8 w-72" /><Skeleton className="h-64 w-full" /></div>
  if (article.error) {
    const missing = article.error instanceof ApiError && article.error.status === 404
    return <div className="mx-auto max-w-3xl space-y-4"><BackLink workspaceId={workspace.id} /><ErrorPanel error={article.error} onRetry={missing ? undefined : () => void article.refetch()} title={missing ? 'Article not found' : 'This article could not be loaded'} /></div>
  }

  const a = article.data
  const run = (action: 'publish' | 'unpublish' | 'archive', done: string) =>
    status.mutate(action, { onSuccess: () => toast.success(done), onError: (e) => toast.error(errorMessage(e)) })

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <BackLink workspaceId={workspace.id} />
      {editing ? (
        <EditArticle article={a} onDone={() => setEditing(false)} />
      ) : (
        <>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0 space-y-2">
              <h1 className="font-display text-2xl font-semibold tracking-tight text-balance [overflow-wrap:anywhere]">{a.title}</h1>
              <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                <ArticleStatusBadge status={a.status} />
                <span>Updated {formatDateTime(a.updated_at)}</span>
                {a.categories.length > 0 && <span>· {a.categories.map((c) => c.name).join(', ')}</span>}
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Restricted reason={a.status === 'archived' ? 'Archived articles cannot be edited. Move it back to draft first.' : null}>
                <Button variant="outline" icon={<PencilSimple />} onClick={() => setEditing(true)}>Edit</Button>
              </Restricted>
              {a.status !== 'published' && <Button icon={<CloudArrowUp />} loading={status.isPending && status.variables === 'publish'} onClick={() => run('publish', 'Article published.')}>Publish</Button>}
              {a.status !== 'draft' && <Button variant="outline" loading={status.isPending && status.variables === 'unpublish'} onClick={() => run('unpublish', 'Moved back to draft.')}>Unpublish</Button>}
              {a.status !== 'archived' && <Button variant="outline" icon={<Archive />} loading={status.isPending && status.variables === 'archive'} onClick={() => run('archive', 'Article archived.')}>Archive</Button>}
              <Button variant="destructive" icon={<Trash />} onClick={() => setConfirmDelete(true)}>Delete</Button>
            </div>
          </div>
          <div className="rounded-xl border p-5">{a.content?.trim() ? <Markdown>{a.content}</Markdown> : <p className="text-sm text-muted-foreground">This article has no content yet.</p>}</div>
        </>
      )}
      <ConfirmDialog
        open={confirmDelete}
        onOpenChange={setConfirmDelete}
        title="Delete this article?"
        description={`"${a.title}" is deleted for everyone. This cannot be undone.`}
        confirmLabel="Delete article"
        destructive
        onConfirm={() =>
          remove.mutate(undefined, {
            onSuccess: () => {
              toast.success('Article deleted.')
              void navigate({ to: `/app/${workspace.id}/knowledge` as never })
            },
            onError: (e) => toast.error(errorMessage(e)),
          })
        }
      />
    </div>
  )
}
