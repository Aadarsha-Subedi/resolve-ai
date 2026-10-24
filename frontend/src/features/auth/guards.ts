import { redirect } from '@tanstack/react-router'
import type { QueryClient } from '@tanstack/react-query'

import { currentUserQuery } from '@/features/auth/api'

/** The signed-in user, or null when signed out or when the check itself fails (the page then decides). */
async function signedInUser(queryClient: QueryClient) {
  try {
    return await queryClient.fetchQuery(currentUserQuery)
  } catch {
    return undefined
  }
}

/** The landing page: a signed-in user goes straight to the app. */
export async function redirectIfSignedIn({ context }: { context: { queryClient: QueryClient } }) {
  if (await signedInUser(context.queryClient)) throw redirect({ to: '/app', replace: true })
}

/** Protected pages (/app/*): a signed-out user goes to the landing page, where Google sign-in starts. */
export async function requireSignedIn({ context }: { context: { queryClient: QueryClient } }) {
  if ((await signedInUser(context.queryClient)) === null) throw redirect({ to: '/', replace: true })
}
