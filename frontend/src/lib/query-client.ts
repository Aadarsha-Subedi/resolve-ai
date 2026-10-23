import { MutationCache, QueryCache, QueryClient } from '@tanstack/react-query'

import { ApiError } from '@/lib/api'

/** A 401 on any call means the session ended: go to sign-in (a full load clears every cache). */
function signedOut(error: unknown) {
  if (error instanceof ApiError && error.status === 401 && window.location.pathname !== '/') window.location.assign('/')
}

/**
 * No retries, no refetch on focus/reconnect, no polling. Data changes when the user acts (a write
 * updates or invalidates only what it affects) or reloads the page; the one sync action is the
 * explicit "Sync latest mails" button.
 */
export const queryClient = new QueryClient({
  queryCache: new QueryCache({ onError: signedOut }),
  mutationCache: new MutationCache({ onError: signedOut }),
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      retry: false,
      refetchOnWindowFocus: false,
      refetchOnReconnect: false,
      refetchInterval: false,
    },
    mutations: { retry: false },
  },
})
