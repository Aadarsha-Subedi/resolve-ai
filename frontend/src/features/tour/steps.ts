export type TourStep = {
  /** CSS selector of the element to spotlight; without one (or when it is not on screen) the card sits mid-page. */
  target?: string
  title: string
  body: string
}

export type TourPage = 'dashboard' | 'tickets' | 'ticket' | 'knowledge' | 'ask' | 'members' | 'settings'

const nav = (slug: string) => `nav[aria-label="Main"] a[href$="/${slug}"]`

export const TOUR_STEPS: Record<TourPage, TourStep[]> = {
  dashboard: [
    { target: 'main h1', title: 'Your desk at a glance', body: 'The dashboard summarises the queue: what is open, what is late and how fast the team answers.' },
    { target: nav('tickets'), title: 'Tickets live here', body: 'Every customer request becomes a ticket. Open the list to work through them.' },
    { target: 'header', title: 'Search and shortcuts', body: 'Press Ctrl+K (or Cmd+K) to jump anywhere, and ? to see every keyboard shortcut.' },
  ],
  tickets: [
    { target: 'main h1', title: 'The queue', body: 'Late and at-risk tickets sort first, so the fire is always at the top.' },
    { target: 'main table', title: 'Open a ticket', body: 'Each row shows status, priority, owner and channel. Click a row to read the conversation and reply.' },
    { title: 'Filter and sort', body: 'Use the filters above the list to narrow by status, priority or assignee. The sample tickets cover every state.' },
  ],
  ticket: [
    { target: 'main h1', title: 'One customer, one thread', body: 'The full conversation is here, with internal notes kept apart from replies the customer sees.' },
    { title: 'Reply, assign, resolve', body: 'Change status, priority and owner from the panel beside the thread. Every change lands in the ticket history.' },
  ],
  knowledge: [
    { target: 'main h1', title: 'Your knowledge base', body: 'Write an answer once and keep it here as an article. This demo starts empty so you can add your own.' },
    { title: 'Articles and files', body: 'Add articles by hand or upload files. Agents search this base while they answer, and the Ask page cites it.' },
    { title: 'Categories', body: 'Group content by category from Settings, so the next person finds the right answer first.' },
  ],
  ask: [
    { target: 'main h1', title: 'Ask your desk', body: 'Ask a question in plain language. The answer is written from your knowledge base and cites its sources.' },
    { title: 'Your history is private', body: 'Past questions are saved per person, per workspace. Nobody else sees them. The demo starts with no chats.' },
    { title: 'Free to try', body: 'Questions use ResolveAI’s free model under a daily allowance. Add your own key in Settings for more.' },
  ],
  members: [
    { target: 'main h1', title: 'Your team', body: 'Everyone in the workspace is listed here with their role.' },
    { title: 'Invite people', body: 'Invite by email or share a join link. The demo is private to you, so inviting is off here.' },
  ],
  settings: [
    { target: 'main h1', title: 'Workspace settings', body: 'Name, logo, customer portal, categories and AI options live here.' },
    { target: '#danger', title: 'Reset or delete', body: 'In the demo you can reset the sample tickets or delete the workspace. You can bring it back from Create workspace.' },
  ],
}

const NON_WORKSPACE = new Set(['account', 'email', 'invitations', 'new'])

/** Which tour a pathname belongs to, or null for pages without one (account, email, invitations, ...). */
export function tourPageFor(pathname: string): TourPage | null {
  const rest = pathname.match(/^\/app\/([^/]+)(?:\/(.*))?$/)
  if (!rest || NON_WORKSPACE.has(rest[1])) return null
  const [section = '', child] = (rest[2] ?? '').split('/')
  if (section === '') return 'dashboard'
  if (section === 'tickets') return child ? 'ticket' : 'tickets'
  if (section === 'knowledge' || section === 'ask' || section === 'members' || section === 'settings') return section
  return null
}
