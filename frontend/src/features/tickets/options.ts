import { PRIORITY_OPTIONS } from '@/components/patterns/ticket-meta'

/** The backend has no "none" priority. */
export const REAL_PRIORITIES = PRIORITY_OPTIONS.filter((o) => o.value !== 'none')
