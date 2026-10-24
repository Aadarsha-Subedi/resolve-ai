import { queryOptions } from '@tanstack/react-query'

import { ApiError, api } from '@/lib/api'

/** GET /api/me/ (backend accounts.serializers.responses.ProfileData). */
export type CurrentUser = { id: string; email: string; display_name: string; avatar_url: string | null; created_at: string }

/** A 401/403 from /me/ means "signed out", not an error. */
export const currentUserQuery = queryOptions({
  queryKey: ['auth', 'me'],
  queryFn: async (): Promise<CurrentUser | null> => {
    try {
      return (await api.get<CurrentUser>('/me/')).data
    } catch (error) {
      if (error instanceof ApiError && (error.status === 401 || error.status === 403)) return null
      throw error
    }
  },
  // Route guards ask on every navigation; a session does not change that fast, and any 401 on a data call signs the user out.
  staleTime: 15 * 60_000,
})

/**
 * Sign-in is a full-page redirect: the browser navigates to the backend's start endpoint, which
 * sends it to Google and, after the callback, back to FRONTEND_URL + `next` (default /app).
 * `remember` keeps the session for the long lifetime. Failures return to /?google_error=<code>.
 */
export function googleStartUrl({ next, remember = false }: { next?: string; remember?: boolean } = {}) {
  const params = new URLSearchParams({ remember: remember ? '1' : '0' })
  if (next) params.set('next', next)
  return `/api/auth/google/start/?${params}`
}

/** Sets the csrftoken cookie that the client echoes as X-CSRFToken. Call once before the first write. */
export const ensureCsrfCookie = () => api.get('/csrf/')

/** Values of /?google_error=<code>, from the backend's accounts.constants.errors. */
export const GOOGLE_ERROR_MESSAGES: Record<string, string> = {
  cancelled: 'Sign-in was cancelled. Try again when you are ready.',
  google_failed: 'Google sign-in did not finish. Try again.',
  rate_limited: 'Too many attempts. Wait a minute, then try again.',
  email_unverified: 'Google reports that email address as unverified. Verify it with Google, then try again.',
  email_conflict: 'That email is already tied to another account. Use the sign-in you first created it with.',
  account_disabled: 'This account is disabled. Contact support.',
}
