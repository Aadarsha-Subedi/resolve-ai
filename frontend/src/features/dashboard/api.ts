import { useQuery } from '@tanstack/react-query'

import { api } from '@/lib/api'
import type { TicketCategoryValue, TicketPriorityValue, TicketStatusValue } from '@/lib/types'

/** Response of GET /workspaces/{id}/dashboard/ (backend/docs/DASHBOARD_API.md). */
export type Period = '7d' | '30d' | '90d'

export type Dashboard = {
  generated_at: string
  period: { key: Period | 'custom'; from: string; to: string; days: number; tz: string; previous: { from: string; to: string } }
  summary: {
    active: number
    by_status: { open: number; in_progress: number; pending: number }
    urgent: number
    high: number
    waiting_for_reply: number
    created: { current: number; previous: number }
    resolved: { current: number; previous: number }
  }
  volume: { granularity: 'day' | 'week'; buckets: { start: string; end: string; created: number; resolved: number }[] }
  recent_tickets: {
    items: { id: string; number: number; subject: string; customer_name: string; status: TicketStatusValue; priority: TicketPriorityValue; category: TicketCategoryValue; waiting_for_reply: boolean; created_at: string; last_activity_at: string }[]
  }
  waiting: {
    total: number
    items: { id: string; number: number; subject: string; customer_name: string; status: TicketStatusValue; priority: TicketPriorityValue; waiting_since: string }[]
  }
  activity: {
    items: {
      id: string
      source: 'ticket'
      event_type: string
      ticket: { id: string; number: number; subject: string }
      actor: { id: string; name: string } | null
      old_value: string | null
      new_value: string | null
      created_at: string
    }[]
  }
}

/** Browsers can report legacy zone names (for example Asia/Katmandu); the API wants the canonical IANA name. */
const ALIASES: Record<string, string> = {
  'Asia/Katmandu': 'Asia/Kathmandu',
  'Asia/Calcutta': 'Asia/Kolkata',
  'Asia/Saigon': 'Asia/Ho_Chi_Minh',
  'Asia/Rangoon': 'Asia/Yangon',
  'Asia/Dacca': 'Asia/Dhaka',
  'Europe/Kiev': 'Europe/Kyiv',
  'America/Buenos_Aires': 'America/Argentina/Buenos_Aires',
  'America/Indianapolis': 'America/Indiana/Indianapolis',
  'US/Eastern': 'America/New_York',
  'US/Central': 'America/Chicago',
  'US/Mountain': 'America/Denver',
  'US/Pacific': 'America/Los_Angeles',
  GMT: 'UTC',
  'Etc/UTC': 'UTC',
}

export function canonicalTimeZone(name: string | undefined): string {
  if (!name) return 'UTC'
  return ALIASES[name] ?? name
}

export const browserTimeZone = () => canonicalTimeZone(Intl.DateTimeFormat().resolvedOptions().timeZone)

/** The whole dashboard in one request; the period and the browser's time zone are the only inputs. */
export type DashboardRange = { period: Period } | { from: string; to: string }

export function useDashboard(ws: string, range: DashboardRange) {
  const tz = browserTimeZone()
  return useQuery({
    queryKey: ['ws', ws, 'dashboard', range, tz],
    queryFn: async ({ signal }) => (await api.get<Dashboard>(`/workspaces/${ws}/dashboard/`, { ...range, tz }, signal)).data,
  })
}
