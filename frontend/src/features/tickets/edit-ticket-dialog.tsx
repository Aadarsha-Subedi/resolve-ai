import { useState, type FormEvent } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Field, FieldError, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { FloppyDisk, X } from '@/icons'
import { useUpdateTicket, type TicketChanges } from '@/features/tickets/api'
import { errorMessage, fieldError } from '@/lib/api'
import type { TicketDetail } from '@/lib/types'

export function EditTicketDialog({ workspaceId, ticket, open, onOpenChange }: { workspaceId: string; ticket: TicketDetail; open: boolean; onOpenChange: (open: boolean) => void }) {
  const update = useUpdateTicket(workspaceId, ticket.id)
  const [subject, setSubject] = useState(ticket.subject)
  const [description, setDescription] = useState(ticket.description)
  const [name, setName] = useState(ticket.customer_name)
  const [email, setEmail] = useState(ticket.customer_email)
  const err = (field: string) => fieldError(update.error, field)

  const submit = (event: FormEvent) => {
    event.preventDefault()
    const changes: TicketChanges = {}
    if (subject.trim() !== ticket.subject) changes.subject = subject.trim()
    if (description.trim() !== ticket.description) changes.description = description.trim()
    if (name.trim() !== ticket.customer_name) changes.customer_name = name.trim()
    if (email.trim() !== ticket.customer_email) changes.customer_email = email.trim()
    if (Object.keys(changes).length === 0) return onOpenChange(false)
    update.mutate(changes, {
      onSuccess: () => {
        toast.success('Ticket updated.')
        onOpenChange(false)
      },
      onError: (e) => {
        if (!['subject', 'description', 'customer_name', 'customer_email'].some((f) => fieldError(e, f))) toast.error(errorMessage(e))
      },
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Edit ticket #{ticket.number}</DialogTitle>
          <DialogDescription>Changing the customer's email changes where replies are sent.</DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="space-y-4">
          <Field>
            <FieldLabel htmlFor="et-subject">Subject</FieldLabel>
            <Input id="et-subject" value={subject} onChange={(e) => setSubject(e.target.value)} maxLength={200} required aria-invalid={!!err('subject')} />
            <FieldError>{err('subject')}</FieldError>
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field>
              <FieldLabel htmlFor="et-name">Customer name</FieldLabel>
              <Input id="et-name" value={name} onChange={(e) => setName(e.target.value)} maxLength={100} />
            </Field>
            <Field>
              <FieldLabel htmlFor="et-email">Customer email</FieldLabel>
              <Input id="et-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required aria-invalid={!!err('customer_email')} />
              <FieldError>{err('customer_email')}</FieldError>
            </Field>
          </div>
          <Field>
            <FieldLabel htmlFor="et-description">Description</FieldLabel>
            <Textarea id="et-description" value={description} onChange={(e) => setDescription(e.target.value)} rows={6} maxLength={20000} required aria-invalid={!!err('description')} />
            <FieldError>{err('description')}</FieldError>
          </Field>
          <DialogFooter>
            <Button type="button" variant="outline" icon={<X />} onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" icon={<FloppyDisk />} loading={update.isPending}>Save changes</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
