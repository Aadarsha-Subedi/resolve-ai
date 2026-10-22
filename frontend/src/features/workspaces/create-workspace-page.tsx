import { useNavigate } from '@tanstack/react-router'
import { useState, type FormEvent } from 'react'
import { toast } from 'sonner'

import { PageHeader } from '@/components/patterns/page-header'
import { Button } from '@/components/ui/button'
import { Field, FieldDescription, FieldError, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { useCreateWorkspace } from '@/features/workspaces/api'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { errorMessage, fieldError } from '@/lib/api'

export function CreateWorkspacePage() {
  useDocumentTitle('New workspace · ResolveAI')
  const navigate = useNavigate()
  const create = useCreateWorkspace()
  const [name, setName] = useState('')
  const [slug, setSlug] = useState('')

  const submit = (event: FormEvent) => {
    event.preventDefault()
    create.mutate(
      { name: name.trim(), slug: slug.trim() || undefined },
      {
        onSuccess: (workspace) => void navigate({ to: `/app/${workspace.id}` as never }),
        onError: (error) => {
          if (!fieldError(error, 'name') && !fieldError(error, 'slug')) toast.error(errorMessage(error))
        },
      },
    )
  }

  return (
    <div className="mx-auto max-w-lg space-y-6">
      <PageHeader title="Create a workspace" description="A workspace is one support desk: its tickets, knowledge base, members and public portal." />
      <form onSubmit={submit} className="space-y-4">
        <Field>
          <FieldLabel htmlFor="ws-name">Name</FieldLabel>
          <Input id="ws-name" value={name} onChange={(e) => setName(e.target.value)} maxLength={80} required autoFocus aria-invalid={!!fieldError(create.error, 'name')} />
          <FieldError>{fieldError(create.error, 'name')}</FieldError>
        </Field>
        <Field>
          <FieldLabel htmlFor="ws-slug">Portal address (optional)</FieldLabel>
          <Input id="ws-slug" value={slug} onChange={(e) => setSlug(e.target.value.toLowerCase())} placeholder="acme-support" aria-invalid={!!fieldError(create.error, 'slug')} />
          <FieldDescription>Customers submit tickets at /portal/{slug || 'your-address'}. 3 to 40 lowercase letters, digits or hyphens. It cannot be changed later.</FieldDescription>
          <FieldError>{fieldError(create.error, 'slug')}</FieldError>
        </Field>
        <Button type="submit" loading={create.isPending} disabled={!name.trim()}>Create workspace</Button>
      </form>
    </div>
  )
}
