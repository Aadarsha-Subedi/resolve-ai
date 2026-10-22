import { useNavigate } from '@tanstack/react-router'
import { useState, type FormEvent } from 'react'
import { toast } from 'sonner'

import { OptionSelect } from '@/components/patterns/option-select'
import { CATEGORY_OPTIONS } from '@/components/patterns/ticket-meta'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Field, FieldError, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Plus, X } from '@/icons'
import { REAL_PRIORITIES } from '@/features/tickets/options'
import { useCreateTicket } from '@/features/tickets/api'
import { errorMessage, fieldError } from '@/lib/api'
import type { TicketCategoryValue, TicketPriorityValue } from '@/lib/types'

/** Agents log a ticket for a customer (phone call, walk-in). Customers use the public portal instead. */
export function NewTicketDialog({ workspaceId, open, onOpenChange }: { workspaceId: string; open: boolean; onOpenChange: (open: boolean) => void }) {
  const navigate = useNavigate()
  const create = useCreateTicket(workspaceId)
  const [subject, setSubject] = useState('')
  const [description, setDescription] = useState('')
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [category, setCategory] = useState<TicketCategoryValue>('general')
  const [priority, setPriority] = useState<TicketPriorityValue>('medium')
  const err = (field: string) => fieldError(create.error, field)

  const submit = (event: FormEvent) => {
    event.preventDefault()
    create.mutate(
      { subject: subject.trim(), description: description.trim(), customer_email: email.trim(), customer_name: name.trim() || undefined, category, priority },
      {
        onSuccess: (ticket) => {
          toast.success(`Ticket #${ticket.number} created.`)
          onOpenChange(false)
          void navigate({ to: `/app/${workspaceId}/tickets/${ticket.id}` as never })
        },
        onError: (e) => {
          if (!['subject', 'description', 'customer_email', 'customer_name'].some((f) => fieldError(e, f))) toast.error(errorMessage(e))
        },
      },
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>New ticket</DialogTitle>
          <DialogDescription>Log a request for a customer. They are emailed when you reply.</DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="space-y-4">
          <Field>
            <FieldLabel htmlFor="nt-subject">Subject</FieldLabel>
            <Input id="nt-subject" value={subject} onChange={(e) => setSubject(e.target.value)} maxLength={200} required aria-invalid={!!err('subject')} />
            <FieldError>{err('subject')}</FieldError>
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field>
              <FieldLabel htmlFor="nt-email">Customer email</FieldLabel>
              <Input id="nt-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required aria-invalid={!!err('customer_email')} />
              <FieldError>{err('customer_email')}</FieldError>
            </Field>
            <Field>
              <FieldLabel htmlFor="nt-name">Customer name (optional)</FieldLabel>
              <Input id="nt-name" value={name} onChange={(e) => setName(e.target.value)} maxLength={100} />
            </Field>
          </div>
          <Field>
            <FieldLabel htmlFor="nt-description">What do they need?</FieldLabel>
            <Textarea id="nt-description" value={description} onChange={(e) => setDescription(e.target.value)} rows={5} maxLength={20000} required aria-invalid={!!err('description')} />
            <FieldError>{err('description')}</FieldError>
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field>
              <FieldLabel htmlFor="nt-category">Category</FieldLabel>
              <OptionSelect id="nt-category" value={category} onValueChange={(v) => setCategory(v as TicketCategoryValue)} options={CATEGORY_OPTIONS} />
            </Field>
            <Field>
              <FieldLabel htmlFor="nt-priority">Priority</FieldLabel>
              <OptionSelect id="nt-priority" value={priority} onValueChange={(v) => setPriority(v as TicketPriorityValue)} options={REAL_PRIORITIES} />
            </Field>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" icon={<X />} onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" icon={<Plus weight="bold" />} loading={create.isPending} disabled={!subject.trim() || !description.trim() || !email.trim()}>Create ticket</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
