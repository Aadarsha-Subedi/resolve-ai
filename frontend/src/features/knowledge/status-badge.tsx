import { SoftBadge, type Tone } from '@/components/patterns/ticket-meta'
import type { SelectOption } from '@/components/patterns/ticket-meta'
import type { ArticleStatus } from '@/features/knowledge/api'
import { Archive, CheckCircle, PencilSimpleLine } from '@/icons'

const META: Record<ArticleStatus, { label: string; tone: Tone; Icon: SelectOption['icon'] }> = {
  draft: { label: 'Draft', tone: 'neutral', Icon: PencilSimpleLine },
  published: { label: 'Published', tone: 'success', Icon: CheckCircle },
  archived: { label: 'Archived', tone: 'warning', Icon: Archive },
}

export function ArticleStatusBadge({ status }: { status: ArticleStatus }) {
  const { label, tone, Icon } = META[status]
  return <SoftBadge tone={tone} icon={Icon}>{label}</SoftBadge>
}
