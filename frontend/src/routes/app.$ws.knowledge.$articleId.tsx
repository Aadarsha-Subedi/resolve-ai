import { createFileRoute } from '@tanstack/react-router'

import { ArticlePage } from '@/features/knowledge/article-page'

export const Route = createFileRoute('/app/$ws/knowledge/$articleId')({ component: Page })

function Page() {
  const { articleId } = Route.useParams()
  return <ArticlePage key={articleId} articleId={articleId} />
}
