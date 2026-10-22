import type { SelectOption } from '@/components/patterns/ticket-meta'
import type { ArticleStatus } from '@/features/knowledge/api'
import { Archive, CheckCircle, PencilSimpleLine } from '@/icons'

const ICON = { draft: PencilSimpleLine, published: CheckCircle, archived: Archive } as const
const LABEL = { draft: 'Draft', published: 'Published', archived: 'Archived' } as const

export const ARTICLE_STATUS_OPTIONS: SelectOption[] = (Object.keys(LABEL) as ArticleStatus[]).map((v) => ({ value: v, label: LABEL[v], icon: ICON[v] }))
