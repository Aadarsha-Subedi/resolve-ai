import { useState } from 'react'

import { Markdown } from '@/components/patterns/markdown'
import { Button } from '@/components/ui/button'
import { DropdownMenu, DropdownMenuCheckboxItem, DropdownMenuContent, DropdownMenuGroup, DropdownMenuLabel, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { Field, FieldDescription, FieldError, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import { useCategories, type Category } from '@/features/knowledge/api'
import { Eye, PencilSimpleLine, Tag } from '@/icons'
import { fieldError } from '@/lib/api'

export type EditorValue = { title: string; content: string; categories: Category[] }

/** Title, Markdown body with a preview tab, and a category picker that fetches categories only when opened. */
export function ArticleEditor({ workspaceId, value, onChange, error }: { workspaceId: string; value: EditorValue; onChange: (value: EditorValue) => void; error: unknown }) {
  const [tab, setTab] = useState<'write' | 'preview'>('write')
  const [pickerOpened, setPickerOpened] = useState(false)
  const categories = useCategories(workspaceId, pickerOpened)
  const selected = new Set(value.categories.map((c) => c.id))
  const toggle = (category: Category, on: boolean) =>
    onChange({ ...value, categories: on ? [...value.categories, category] : value.categories.filter((c) => c.id !== category.id) })

  return (
    <div className="space-y-4">
      <Field>
        <FieldLabel htmlFor="art-title">Title</FieldLabel>
        <Input id="art-title" value={value.title} maxLength={200} onChange={(e) => onChange({ ...value, title: e.target.value })} aria-invalid={!!fieldError(error, 'title')} />
        <FieldError>{fieldError(error, 'title')}</FieldError>
      </Field>

      <div className="flex flex-wrap items-center gap-2">
        <DropdownMenu onOpenChange={(open) => open && setPickerOpened(true)}>
          <DropdownMenuTrigger render={<Button variant="outline" icon={<Tag />}>Categories{selected.size ? ` (${selected.size})` : ''}</Button>} />
          <DropdownMenuContent align="start" className="w-60">
            <DropdownMenuGroup>
              <DropdownMenuLabel>Choose up to 10</DropdownMenuLabel>
              {categories.isPending && pickerOpened ? <p className="px-2 py-1.5 text-xs text-muted-foreground">Loading…</p> : null}
              {categories.data?.map((c) => (
                <DropdownMenuCheckboxItem key={c.id} checked={selected.has(c.id)} onCheckedChange={(on) => toggle(c, !!on)}>{c.name}</DropdownMenuCheckboxItem>
              ))}
              {categories.error ? <p className="px-2 py-1.5 text-xs text-destructive">Categories could not be loaded.</p> : null}
            </DropdownMenuGroup>
          </DropdownMenuContent>
        </DropdownMenu>
        <span className="text-sm text-muted-foreground">{value.categories.map((c) => c.name).join(', ') || 'No categories'}</span>
      </div>

      <Field>
        <div className="flex items-center justify-between gap-3">
          <FieldLabel htmlFor="art-content">Content (Markdown)</FieldLabel>
          <Tabs value={tab} onValueChange={(v) => setTab(v as 'write' | 'preview')}>
            <TabsList>
              <TabsTrigger value="write"><PencilSimpleLine />Write</TabsTrigger>
              <TabsTrigger value="preview"><Eye />Preview</TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
        {tab === 'write' ? (
          <Textarea id="art-content" rows={18} value={value.content} onChange={(e) => onChange({ ...value, content: e.target.value })} className="font-mono text-[0.8125rem]" aria-invalid={!!fieldError(error, 'content')} />
        ) : (
          <div className="min-h-64 rounded-lg border p-4">{value.content.trim() ? <Markdown>{value.content}</Markdown> : <p className="text-sm text-muted-foreground">Nothing to preview yet.</p>}</div>
        )}
        <FieldDescription>Up to 200 KB. Headings, lists, links, code and tables are supported; raw HTML is not rendered.</FieldDescription>
        <FieldError>{fieldError(error, 'content')}</FieldError>
      </Field>
    </div>
  )
}
