import type { TicketEvent } from '@/lib/types'

const STATUS_LABEL: Record<string, string> = { open: 'Open', in_progress: 'In progress', pending: 'Pending', resolved: 'Resolved', closed: 'Closed' }
const word = (value: unknown) => (typeof value === 'string' ? (STATUS_LABEL[value] ?? value.replace(/_/g, ' ')) : '')

const person = (value: unknown): string | null =>
  value && typeof value === 'object' && 'display_name' in value && typeof value.display_name === 'string' ? value.display_name : null

/** One plain sentence for a history entry. Event rows carry ids and values only, never message text. */
export function describeEvent(event: TicketEvent): string {
  switch (event.event_type) {
    case 'created':
      return event.metadata.source === 'portal' ? 'Submitted through the portal' : event.metadata.source === 'email' ? 'Created from an email' : 'Ticket created'
    case 'status_changed':
      return `Status changed from ${word(event.old_value)} to ${word(event.new_value)}`
    case 'priority_changed':
      return `Priority changed from ${word(event.old_value)} to ${word(event.new_value)}`
    case 'category_changed':
      return `Category changed from ${word(event.old_value)} to ${word(event.new_value)}`
    case 'assignee_changed': {
      const to = person(event.new_value)
      const from = person(event.old_value)
      if (event.metadata.reason === 'member_left' || event.metadata.reason === 'member_removed') return `Unassigned because ${from ?? 'the assignee'} ${event.metadata.reason === 'member_left' ? 'left the workspace' : 'was removed from the workspace'}`
      if (to && from) return `Reassigned from ${from} to ${to}`
      return to ? `Assigned to ${to}` : from ? `Unassigned from ${from}` : 'Assignee changed'
    }
    case 'details_changed':
      return 'Details edited'
    case 'public_reply_added':
      return 'Reply sent to the customer'
    case 'internal_note_added':
      return 'Internal note added'
    case 'customer_reply_received':
      return 'Customer replied'
    case 'email_delivery_failed':
      return 'A reply could not be delivered'
    default:
      return event.event_type.replace(/_/g, ' ')
  }
}
