import { useState, type FormEvent } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { ErrorPanel, LinesSkeleton } from '@/features/app/page-states'
import { useCategories, useCategoryMutations, type Category } from '@/features/knowledge/api'
import { Check, Pencil, Plus, Trash } from '@/icons'
import { errorMessage } from '@/lib/api'

function CategoryRow({ workspaceId, category }: { workspaceId: string; category: Category }) {
  const { rename, remove } = useCategoryMutations(workspaceId)
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState(category.name)
  const save = (event: FormEvent) => {
    event.preventDefault()
    rename.mutate({ id: category.id, name: name.trim() }, { onSuccess: () => setEditing(false), onError: (e) => toast.error(errorMessage(e)) })
  }
  return (
    <li className="flex items-center gap-2 py-1.5">
      {editing ? (
        <form onSubmit={save} className="flex flex-1 items-center gap-2">
          <Input value={name} onChange={(e) => setName(e.target.value)} maxLength={60} aria-label="Category name" autoFocus />
          <Button type="submit" size="icon-sm" variant="outline" label="Save name" loading={rename.isPending}><Check /></Button>
        </form>
      ) : (
        <>
          <span className="min-w-0 flex-1 truncate text-sm">{category.name}</span>
          <Button size="icon-sm" variant="ghost" label={`Rename ${category.name}`} onClick={() => setEditing(true)}><Pencil /></Button>
          <Button size="icon-sm" variant="ghost" label={`Delete ${category.name}`} loading={remove.isPending} onClick={() => remove.mutate(category.id, { onError: (e) => toast.error(errorMessage(e)) })}><Trash /></Button>
        </>
      )}
    </li>
  )
}

/** Add, rename and delete categories. Deleting only unlinks it from articles. Fetches when opened. */
export function ManageCategoriesDialog({ workspaceId, open, onOpenChange }: { workspaceId: string; open: boolean; onOpenChange: (open: boolean) => void }) {
  const categories = useCategories(workspaceId, open)
  const { create } = useCategoryMutations(workspaceId)
  const [name, setName] = useState('')
  const add = (event: FormEvent) => {
    event.preventDefault()
    create.mutate(name.trim(), { onSuccess: () => setName(''), onError: (e) => toast.error(errorMessage(e)) })
  }
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Categories</DialogTitle>
          <DialogDescription>Group articles. Deleting a category keeps its articles.</DialogDescription>
        </DialogHeader>
        {categories.isPending ? <LinesSkeleton rows={3} /> : categories.error ? <ErrorPanel error={categories.error} onRetry={() => void categories.refetch()} /> : (
          <ul className="max-h-64 divide-y overflow-y-auto">{categories.data.map((c) => <CategoryRow key={c.id} workspaceId={workspaceId} category={c} />)}</ul>
        )}
        <form onSubmit={add} className="flex items-center gap-2">
          <Input value={name} onChange={(e) => setName(e.target.value)} maxLength={60} placeholder="New category" aria-label="New category name" />
          <Button type="submit" variant="outline" icon={<Plus />} loading={create.isPending} disabled={!name.trim()}>Add</Button>
        </form>
      </DialogContent>
    </Dialog>
  )
}
