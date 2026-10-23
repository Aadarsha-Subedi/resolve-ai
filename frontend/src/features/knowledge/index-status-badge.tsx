import { SoftBadge, type Tone } from '@/components/patterns/ticket-meta'
import type { IndexStatus } from '@/features/knowledge/api'

const META: Record<IndexStatus, { label: string; tone: Tone }> = {
  pending: { label: 'Waiting to be read', tone: 'neutral' },
  indexing: { label: 'Reading', tone: 'info' },
  indexed: { label: 'Searchable', tone: 'success' },
  failed: { label: 'Could not be read', tone: 'danger' },
}

export function IndexStatusBadge({ status }: { status: IndexStatus }) {
  const { label, tone } = META[status]
  return <SoftBadge tone={tone}>{label}</SoftBadge>
}
