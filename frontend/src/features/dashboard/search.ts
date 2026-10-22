import type { Period } from '@/features/dashboard/api'
import { parseIsoDate } from '@/lib/date'

/** `period` presets, or a custom `from`/`to` range (at most 366 days, as the backend allows). */
export type DashboardSearch = { period?: Period; from?: string; to?: string }
export const PERIODS: { value: Period; label: string; days: number }[] = [
  { value: '7d', label: '7 days', days: 7 },
  { value: '30d', label: '30 days', days: 30 },
  { value: '90d', label: '90 days', days: 90 },
]
export const MAX_CUSTOM_DAYS = 366

export function validateDashboardSearch(search: Record<string, unknown>): DashboardSearch {
  const from = parseIsoDate(search.from as string)
  const to = parseIsoDate(search.to as string)
  if (from && to && from <= to && Math.round((to.getTime() - from.getTime()) / 86_400_000) + 1 <= MAX_CUSTOM_DAYS) {
    return { from: search.from as string, to: search.to as string }
  }
  return { period: search.period === '7d' || search.period === '90d' ? search.period : undefined }
}
