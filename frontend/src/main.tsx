import { QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider, createRouter } from '@tanstack/react-router'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { queryClient } from '@/lib/query-client'
import { ErrorBoundary } from '@/components/patterns/error-boundary'
import { ErrorScreen } from '@/components/patterns/error-screen'
import { NotFoundScreen } from '@/components/patterns/not-found-screen'
import { PageLoading } from '@/components/patterns/page-loading'
import { routeTree } from '@/routeTree.gen'
import './index.css'

const router = createRouter({
  routeTree,
  context: { queryClient },
  defaultPreload: 'intent',
  // Route code is split, so a route can be pending while its chunk loads; any route crash shows the error screen (reload, no auto retry).
  defaultPendingComponent: () => <PageLoading />,
  defaultPendingMs: 150,
  defaultErrorComponent: ({ error }) => <ErrorScreen error={error} />,
  defaultNotFoundComponent: () => <NotFoundScreen />,
})

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </ErrorBoundary>
  </StrictMode>,
)
