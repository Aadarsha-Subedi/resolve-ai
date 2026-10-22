import type { TicketCategoryValue, TicketPriorityValue, TicketStatusValue } from '@/lib/types'

export type TicketSearch = {
  status?: TicketStatusValue
  priority?: TicketPriorityValue
  category?: TicketCategoryValue
  created_from?: string
  created_to?: string
  q?: string
  waiting_for_reply?: boolean
  /** A member's user id, "me" or "unassigned". */
  assignee?: string
  ordering?: string
  page?: number
}

const STATUSES = ['open', 'in_progress', 'pending', 'resolved', 'closed']
const PRIORITIES = ['low', 'medium', 'high', 'urgent']
const CATEGORIES = ['billing', 'technical', 'account', 'feature_request', 'general', 'other']
const ORDER_FIELDS = ['number', 'created_at', 'updated_at', 'last_activity_at', 'priority', 'status']

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const assignee = (value: unknown) => (typeof value === 'string' && (value === 'me' || value === 'unassigned' || UUID.test(value)) ? value : undefined)
const oneOf = <T extends string>(value: unknown, allowed: string[]): T | undefined => (typeof value === 'string' && allowed.includes(value) ? (value as T) : undefined)
const date = (value: unknown) => (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) ? value : undefined)

/** URL state of the ticket list: unknown or malformed values are dropped instead of reaching the API. */
export function validateTicketSearch(search: Record<string, unknown>): TicketSearch {
  const ordering = typeof search.ordering === 'string' && ORDER_FIELDS.includes(search.ordering.replace(/^-/, '')) ? search.ordering : undefined
  const page = Number(search.page)
  return {
    status: oneOf(search.status, STATUSES),
    priority: oneOf(search.priority, PRIORITIES),
    category: oneOf(search.category, CATEGORIES),
    created_from: date(search.created_from),
    created_to: date(search.created_to),
    q: typeof search.q === 'string' && search.q.trim() ? search.q.trim().slice(0, 100) : undefined,
    waiting_for_reply: search.waiting_for_reply === true || search.waiting_for_reply === 'true' ? true : undefined,
    assignee: assignee(search.assignee),
    ordering,
    page: Number.isInteger(page) && page > 1 ? page : undefined,
  }
}
