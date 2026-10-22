/** Shapes returned by the Django API (field names and lowercase enum values as the backend sends them). */

export type Role = 'owner' | 'member'

export type Workspace = {
  id: string
  name: string
  slug: string
  logo_url: string | null
  portal_enabled: boolean
  created_at: string
  role: Role
}

export type TicketStatusValue = 'open' | 'in_progress' | 'pending' | 'resolved' | 'closed'
export type TicketPriorityValue = 'low' | 'medium' | 'high' | 'urgent'
export type TicketCategoryValue = 'billing' | 'technical' | 'account' | 'feature_request' | 'general' | 'other'
export type TicketSourceValue = 'portal' | 'agent' | 'email'

export type TicketAssignee = { id: string; display_name: string }

export type TicketSummary = {
  id: string
  number: number
  subject: string
  customer_name: string
  customer_email: string
  status: TicketStatusValue
  priority: TicketPriorityValue
  category: TicketCategoryValue
  created_via: TicketSourceValue
  waiting_for_reply: boolean
  assignee: TicketAssignee | null
  created_at: string
  updated_at: string
  last_activity_at: string
}

export type TicketDetail = TicketSummary & {
  description: string
  created_by: string | null
  resolved_at: string | null
  closed_at: string | null
  last_customer_message_at: string | null
  last_agent_reply_at: string | null
}

export type TicketMessage = {
  id: string
  author_type: 'agent' | 'customer' | 'system'
  author: { id: string; display_name: string } | null
  visibility: 'public' | 'internal'
  direction: 'inbound' | 'outbound' | 'internal'
  body: string
  delivery_status: 'queued' | 'sent' | 'failed' | 'received' | null
  created_at: string
}

export type TicketEvent = {
  id: string
  event_type: string
  actor: string | null
  old_value: unknown
  new_value: unknown
  metadata: Record<string, unknown>
  created_at: string
}

export type GmailStatusValue = 'connected' | 'not_connected' | 'reauth_required' | 'disconnected'

export type GmailConnection = {
  status: GmailStatusValue
  mailbox_email?: string
  has_required_scopes?: boolean
  connected_at?: string | null
  last_sync_at?: string | null
  push_active?: boolean
  reconnect_path: string | null
}
