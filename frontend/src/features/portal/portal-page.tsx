import { useState, type FormEvent } from 'react'

import { Logo } from '@/components/patterns/logo'
import { NotFoundScreen } from '@/components/patterns/not-found-screen'
import { OptionSelect } from '@/components/patterns/option-select'
import { CATEGORY_OPTIONS } from '@/components/patterns/ticket-meta'
import { Button } from '@/components/ui/button'
import { Field, FieldDescription, FieldError, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { Textarea } from '@/components/ui/textarea'
import { ErrorPanel } from '@/features/app/page-states'
import { WorkspaceMark } from '@/features/app/workspace-mark'
import { useSubmitPortalTicket, usePortal } from '@/features/portal/api'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { CheckCircle } from '@/icons'
import { ApiError, errorMessage, fieldError } from '@/lib/api'
import type { TicketCategoryValue } from '@/lib/types'

/** Public page for customers: no login, one form. After sending, only the ticket number is shown. */
export function PortalPage({ slug }: { slug: string }) {
  const portal = usePortal(slug)
  const submit = useSubmitPortalTicket(slug)
  useDocumentTitle(portal.data ? `${portal.data.name} support` : 'Support')
  const [subject, setSubject] = useState('')
  const [description, setDescription] = useState('')
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [category, setCategory] = useState<TicketCategoryValue>('general')
  const [website, setWebsite] = useState('')
  const [number, setNumber] = useState<number | null>(null)

  if (portal.error instanceof ApiError && portal.error.status === 404) return <NotFoundScreen />
  const err = (field: string) => fieldError(submit.error, field)

  const send = (event: FormEvent) => {
    event.preventDefault()
    submit.mutate(
      { subject: subject.trim(), description: description.trim(), customer_email: email.trim(), customer_name: name.trim() || undefined, category, website },
      { onSuccess: setNumber },
    )
  }

  return (
    <main className="mx-auto flex min-h-svh w-full max-w-xl flex-col gap-6 px-5 py-10">
      <header className="flex items-center gap-3">
        {portal.data ? <WorkspaceMark workspace={portal.data} size="lg" /> : <Skeleton className="size-10 rounded-md" />}
        <div className="min-w-0">
          {portal.data ? <h1 className="truncate font-display text-2xl font-semibold tracking-tight">{portal.data.name}</h1> : <Skeleton className="h-8 w-48" />}
          <p className="text-sm text-muted-foreground">Send us a request. We reply by email.</p>
        </div>
      </header>

      {portal.error ? (
        <ErrorPanel error={portal.error} onRetry={() => void portal.refetch()} />
      ) : number !== null ? (
        <div role="status" className="space-y-3 rounded-xl border p-5">
          <p className="flex items-center gap-2 text-lg font-semibold"><CheckCircle weight="fill" className="size-6 text-success" aria-hidden />Request received</p>
          <p className="text-sm">Your ticket number is <span className="font-semibold tabular-nums">#{number}</span>. Replies come to {email} by email; there is nothing else to do here.</p>
        </div>
      ) : (
        <form onSubmit={send} className="space-y-4">
          <Field>
            <FieldLabel htmlFor="p-subject">Subject</FieldLabel>
            <Input id="p-subject" value={subject} onChange={(e) => setSubject(e.target.value)} maxLength={200} required aria-invalid={!!err('subject')} />
            <FieldError>{err('subject')}</FieldError>
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field>
              <FieldLabel htmlFor="p-email">Your email</FieldLabel>
              <Input id="p-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" aria-invalid={!!err('customer_email')} />
              <FieldError>{err('customer_email')}</FieldError>
            </Field>
            <Field>
              <FieldLabel htmlFor="p-name">Your name (optional)</FieldLabel>
              <Input id="p-name" value={name} onChange={(e) => setName(e.target.value)} maxLength={100} autoComplete="name" />
            </Field>
          </div>
          <Field>
            <FieldLabel htmlFor="p-category">Topic</FieldLabel>
            <OptionSelect id="p-category" value={category} onValueChange={(v) => setCategory(v as TicketCategoryValue)} options={CATEGORY_OPTIONS} />
          </Field>
          <Field>
            <FieldLabel htmlFor="p-description">How can we help?</FieldLabel>
            <Textarea id="p-description" rows={6} value={description} onChange={(e) => setDescription(e.target.value)} maxLength={20000} required aria-invalid={!!err('description')} />
            <FieldDescription>Plain text. Please do not include passwords.</FieldDescription>
            <FieldError>{err('description')}</FieldError>
          </Field>
          {/* Honeypot: people never see or fill this; bots do. */}
          <div aria-hidden className="absolute -left-[9999px] h-0 w-0 overflow-hidden">
            <label>Website<input type="text" name="website" tabIndex={-1} autoComplete="off" value={website} onChange={(e) => setWebsite(e.target.value)} /></label>
          </div>
          {submit.error && !['subject', 'description', 'customer_email'].some(err) && <p role="alert" className="text-sm text-destructive">{errorMessage(submit.error)}</p>}
          <Button type="submit" loading={submit.isPending} disabled={!portal.data || !subject.trim() || !description.trim() || !email.trim()}>Send request</Button>
        </form>
      )}
      <footer className="mt-auto pt-6 text-xs text-muted-foreground"><Logo className="text-xs" /> support desk</footer>
    </main>
  )
}
