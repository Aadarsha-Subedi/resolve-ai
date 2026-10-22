export type AuditSearch = { action_prefix?: string; created_from?: string; created_to?: string; page?: number }

export const GROUPS = [
  { value: 'workspace.', label: 'Workspace' },
  { value: 'member.', label: 'Members' },
  { value: 'ownership.', label: 'Ownership' },
  { value: 'join_link.', label: 'Join link' },
  { value: 'invitation.', label: 'Invitations' },
  { value: 'ticket.', label: 'Tickets' },
  { value: 'article.', label: 'Articles' },
  { value: 'category.', label: 'Categories' },
  { value: 'upload.', label: 'Files' },
  { value: 'gmail.', label: 'Gmail' },
]

export function validateAuditSearch(search: Record<string, unknown>): AuditSearch {
  const date = (v: unknown) => (typeof v === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(v) ? v : undefined)
  const page = Number(search.page)
  return {
    action_prefix: GROUPS.some((g) => g.value === search.action_prefix) ? (search.action_prefix as string) : undefined,
    created_from: date(search.created_from),
    created_to: date(search.created_to),
    page: Number.isInteger(page) && page > 1 ? page : undefined,
  }
}

