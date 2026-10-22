import { Link, useNavigate } from '@tanstack/react-router'
import { useRef, useState } from 'react'
import { toast } from 'sonner'

import { OptionSelect } from '@/components/patterns/option-select'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Field, FieldLabel } from '@/components/ui/field'
import { useStorage, useUploadFile, useCategories } from '@/features/knowledge/api'
import { Notebook, Tag, UploadSimple, X } from '@/icons'
import { errorMessage } from '@/lib/api'
import { formatBytes } from '@/lib/format'

const MAX_BYTES = 10 * 1024 * 1024
const TYPES = ['application/pdf', 'text/plain']

/**
 * "New": first pick the category, then write an article or upload a file. Both end up under that category
 * (an article can still be given more categories in the editor).
 */
export function NewContentDialog({ workspaceId, open, onOpenChange }: { workspaceId: string; open: boolean; onOpenChange: (open: boolean) => void }) {
  const navigate = useNavigate()
  const categories = useCategories(workspaceId, open)
  const storage = useStorage(workspaceId, open)
  const send = useUploadFile(workspaceId)
  const input = useRef<HTMLInputElement>(null)
  const [chosen, setChosen] = useState<string | undefined>()
  const options = (categories.data ?? []).map((c) => ({ value: c.id, label: c.name, icon: Tag }))
  const category = chosen ?? options[0]?.value
  const full = storage.data ? storage.data.remaining_bytes <= 0 : false

  const write = () => {
    onOpenChange(false)
    void navigate({ to: `/app/${workspaceId}/knowledge/new` as never, search: { category } as never })
  }
  const upload = (file: File | undefined) => {
    if (!file || !category) return
    if (!TYPES.includes(file.type)) return void toast.error('Only PDF and plain text (.txt) files can be uploaded.')
    if (file.size > MAX_BYTES) return void toast.error(`Files can be at most ${formatBytes(MAX_BYTES)}.`)
    if (storage.data && file.size > storage.data.remaining_bytes) return void toast.error('That file is larger than the space left. Delete files first.')
    send.mutate({ file, categoryId: category }, { onSuccess: () => { toast.success(`${file.name} uploaded.`); onOpenChange(false) }, onError: (e) => toast.error(errorMessage(e)) })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add to the knowledge base</DialogTitle>
          <DialogDescription>Choose a category first. The article or file is filed under it.</DialogDescription>
        </DialogHeader>
        {categories.data && options.length === 0 ? (
          <p className="text-sm text-muted-foreground">There are no categories yet. Add one under <Link to={`/app/${workspaceId}/settings` as never} className="font-medium text-foreground underline underline-offset-4" onClick={() => onOpenChange(false)}>Settings</Link> first.</p>
        ) : (
          <Field>
            <FieldLabel htmlFor="new-content-category">Category</FieldLabel>
            <OptionSelect id="new-content-category" value={category} onValueChange={setChosen} options={options} placeholder={categories.isPending ? 'Loading categories…' : 'Choose a category'} disabled={!categories.data} />
          </Field>
        )}
        <input ref={input} type="file" accept=".pdf,.txt,application/pdf,text/plain" className="sr-only" aria-label="Choose a file to upload" onChange={(e) => { upload(e.target.files?.[0]); e.target.value = '' }} />
        <DialogFooter className="sm:flex-wrap">
          <Button type="button" variant="outline" icon={<X />} onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button type="button" variant="outline" icon={<UploadSimple />} loading={send.isPending} disabled={!category || full} title={full ? 'Storage is full. Delete files to upload more.' : undefined} onClick={() => input.current?.click()}>Upload a file</Button>
          <Button type="button" icon={<Notebook />} disabled={!category} onClick={write}>Write an article</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
