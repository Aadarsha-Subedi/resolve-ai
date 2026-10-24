import type { TicketChannel, TicketHealth, TicketPriority, TicketStatus } from "@/components/patterns/ticket-meta"

/** Fake sample data for the preview only. Mirrors the reference screen; never shown as real. */
export interface Ticket {
  id: string
  number: number
  subject: string
  status: TicketStatus
  priority: TicketPriority
  assignee: string | null
  category: string
  channel: TicketChannel
  health: TicketHealth
}

export const TICKETS: Ticket[] = [
  { id: "7", number: 7, subject: "Deactivate unused seats without closing the account", status: "closed", priority: "none", assignee: "Lam Tran", category: "Other", channel: "chat", health: "on_track" },
  { id: "17", number: 17, subject: "Help center article link broken in onboarding email", status: "closed", priority: "none", assignee: "Nhi Pham", category: "Other", channel: "chat", health: "on_track" },
  { id: "1", number: 1, subject: "SSO SAML configuration failing on IdP callback", status: "open", priority: "high", assignee: "Jason Duong", category: "Technical", channel: "email", health: "warning" },
  { id: "2", number: 2, subject: "Webhook delivery delays to our Salesforce endpoint", status: "open", priority: "urgent", assignee: "Jason Duong", category: "Technical", channel: "slack", health: "on_track" },
  { id: "4", number: 4, subject: "Rate limiting our batch export API calls unexpectedly", status: "open", priority: "medium", assignee: "Annie Nguyen", category: "Technical", channel: "email", health: "on_track" },
  { id: "5", number: 5, subject: "Need proration breakdown for yearly invoice", status: "open", priority: "medium", assignee: null, category: "Billing", channel: "chat", health: "warning" },
  { id: "12", number: 12, subject: "Mobile app push notifications missing after latest update", status: "open", priority: "urgent", assignee: "Jason Duong", category: "Technical", channel: "slack", health: "breached" },
  { id: "3", number: 3, subject: "Can we get custom roles and permissions on Growth?", status: "pending", priority: "high", assignee: "Jason Duong", category: "Account", channel: "email", health: "breached" },
  { id: "9", number: 9, subject: "Bulk import failed with UTF-8 CSV names", status: "pending", priority: "high", assignee: "Nhi Pham", category: "Technical", channel: "email", health: "warning" },
  { id: "11", number: 11, subject: "Ask for invoice by legal entity split", status: "resolved", priority: "low", assignee: "Thanh Le", category: "Billing", channel: "chat", health: "on_track" },
]
