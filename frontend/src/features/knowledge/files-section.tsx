import { formatDistanceToNowStrict } from 'date-fns'
import { useState } from 'react'
import { toast } from 'sonner'

import { ConfirmDialog } from '@/components/patterns/confirm-dialog'
import { SoftBadge } from '@/components/patterns/ticket-meta'
import { UsageMeter } from '@/components/patterns/usage-meter'
import { Button } from '@/components/ui/button'
import { EmptyState, ErrorPanel, LinesSkeleton } from '@/features/app/page-states'
import { getDownloadUrl, useDeleteUpload, useStorage, useUploads, type Upload } from '@/features/knowledge/api'
import { IndexStatusBadge } from '@/features/knowledge/index-status-badge'
import { failureMessage } from '@/features/knowledge/upload-failures'
import { DownloadSimple, FileDoc, FilePdf, FileText, Folder, Trash } from '@/icons'
import { errorMessage } from '@/lib/api'
import { formatBytes } from '@/lib/format'

/** Files filed under categories, shown under the articles list on the same page (same category and search filters). */
export function FilesSection({ workspaceId, category, filename }: { workspaceId: string; category?: string; filename?: string }) {
  const uploads = useUploads(workspaceId, { category, filename })
  const storage = useStorage(workspaceId, true)
  const remove = useDeleteUpload(workspaceId)
  const [deleting, setDeleting] = useState<Upload | null>(null)
  const [downloading, setDownloading] = useState<string | null>(null)

  const download = async (upload: Upload) => {
    setDownloading(upload.id)
    try {
      window.open(await getDownloadUrl(workspaceId, upload.id), '_blank', 'noopener,noreferrer')
    } catch (e) {
      toast.error(errorMessage(e))
    } finally {
      setDownloading(null)
    }
  }

  return (
    <section aria-labelledby="files-heading" className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <h2 id="files-heading" className="text-sm font-semibold">Files</h2>
        <div className="w-full max-w-xs">
          {storage.data ? <UsageMeter label="Storage" used={storage.data.used_bytes} limit={storage.data.limit_bytes} format={formatBytes} /> : null}
        </div>
      </div>

      {uploads.isPending ? (
        <LinesSkeleton rows={4} />
      ) : uploads.error ? (
        <ErrorPanel error={uploads.error} onRetry={() => void uploads.refetch()} />
      ) : uploads.data.length === 0 ? (
        <EmptyState icon={Folder} title={category || filename ? 'No files match' : 'No files yet'}>{category || filename ? 'Try another category or search.' : 'Use New to upload PDF, Word, Markdown or text files (up to 10 MB each) under a category. Their text is searched when you ask a question.'}</EmptyState>
      ) : (
        <ul className="divide-y rounded-xl border">
          {uploads.data.map((upload) => {
            const Icon = upload.content_type === 'application/pdf' ? FilePdf : upload.content_type.includes('wordprocessingml') ? FileDoc : FileText
            return (
              <li key={upload.id} className="flex items-center gap-3 p-3">
                <Icon className="size-5 shrink-0 text-muted-foreground" aria-hidden />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium" title={upload.filename}>{upload.filename}</p>
                  <p className="text-xs text-muted-foreground">{upload.category ? `${upload.category.name} · ` : 'Uncategorized · '}{formatBytes(upload.size_bytes)}{upload.page_count ? ` · ${upload.page_count} ${upload.page_count === 1 ? 'page' : 'pages'}` : ''} · {formatDistanceToNowStrict(new Date(upload.created_at), { addSuffix: true })}</p>
                  {upload.index_status === 'failed' && <p className="text-xs text-destructive">{failureMessage(upload.index_error)} It is not searched. Delete it and upload a fixed copy.</p>}
                </div>
                {upload.status === 'pending' ? <SoftBadge tone="warning">Unconfirmed</SoftBadge> : <IndexStatusBadge status={upload.index_status} />}
                <Button variant="outline" size="sm" icon={<DownloadSimple />} loading={downloading === upload.id} disabled={upload.status !== 'ready'} onClick={() => void download(upload)}>Download</Button>
                <Button variant="ghost" size="icon-sm" label={`Delete ${upload.filename}`} onClick={() => setDeleting(upload)}><Trash /></Button>
              </li>
            )
          })}
        </ul>
      )}

      <ConfirmDialog
        open={deleting !== null}
        onOpenChange={(open) => !open && setDeleting(null)}
        title="Delete this file?"
        description={deleting ? `${deleting.filename} is removed for everyone and its ${formatBytes(deleting.size_bytes)} are freed.` : ''}
        confirmLabel="Delete file"
        destructive
        onConfirm={() => deleting && remove.mutate(deleting.id, { onSuccess: () => toast.success('File deleted.'), onError: (e) => toast.error(errorMessage(e)) })}
      />
    </section>
  )
}
