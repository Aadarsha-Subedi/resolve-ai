import { useQuery } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { toast } from 'sonner'

import { ConfirmDialog } from '@/components/patterns/confirm-dialog'
import { PageHeader } from '@/components/patterns/page-header'
import { SoftBadge } from '@/components/patterns/ticket-meta'
import { UserAvatar } from '@/components/patterns/user-avatar'
import { Button } from '@/components/ui/button'
import { Field, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { useDeleteAccount, useRevokeSession, useSessions, useSignOut, useUpdateProfile } from '@/features/account/api'
import { currentUserQuery } from '@/features/auth/api'
import { ErrorPanel, LinesSkeleton } from '@/features/app/page-states'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { Desktop, SignOut, Trash } from '@/icons'
import { errorMessage } from '@/lib/api'
import { formatDateTime } from '@/lib/format'

function ProfileForm({ name }: { name: string }) {
  const update = useUpdateProfile()
  const [value, setValue] = useState(name)
  const submit = (event: FormEvent) => {
    event.preventDefault()
    update.mutate(value.trim(), { onSuccess: () => toast.success('Name updated.'), onError: (e) => toast.error(errorMessage(e)) })
  }
  return (
    <form onSubmit={submit} className="flex flex-wrap items-end gap-3">
      <Field className="w-72 max-w-full">
        <FieldLabel htmlFor="display-name">Display name</FieldLabel>
        <Input id="display-name" value={value} onChange={(e) => setValue(e.target.value)} maxLength={100} required />
      </Field>
      <Button type="submit" variant="outline" loading={update.isPending} disabled={!value.trim() || value.trim() === name}>Save</Button>
    </form>
  )
}

export function AccountPage() {
  useDocumentTitle('Account · ResolveAI')
  const user = useQuery(currentUserQuery)
  const sessions = useSessions()
  const revoke = useRevokeSession()
  const signOut = useSignOut()
  const signOutAll = useSignOut(true)
  const deleteAccount = useDeleteAccount()
  const [confirmDelete, setConfirmDelete] = useState(false)

  return (
    <div className="mx-auto max-w-3xl space-y-10">
      <PageHeader title="Account" description="Your profile and the devices signed in to it." />

      <section aria-labelledby="profile" className="space-y-4">
        <h2 id="profile" className="text-lg font-semibold">Profile</h2>
        {user.isPending ? (
          <Skeleton className="h-16 w-full max-w-md" />
        ) : user.data ? (
          <>
            <div className="flex items-center gap-3">
              <UserAvatar name={user.data.display_name} src={user.data.avatar_url} size="lg" />
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">{user.data.email}</p>
                <p className="text-xs text-muted-foreground">Signed in with Google. Your email comes from Google and cannot be changed here.</p>
              </div>
            </div>
            <ProfileForm key={user.data.display_name} name={user.data.display_name} />
          </>
        ) : null}
      </section>

      <section aria-labelledby="devices" className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 id="devices" className="text-lg font-semibold">Signed-in devices</h2>
          <Button variant="outline" size="sm" icon={<SignOut />} loading={signOutAll.isPending} onClick={() => signOutAll.mutate()}>Sign out everywhere</Button>
        </div>
        {sessions.isPending ? (
          <LinesSkeleton rows={3} />
        ) : sessions.error ? (
          <ErrorPanel error={sessions.error} onRetry={() => void sessions.refetch()} />
        ) : (
          <ul className="divide-y rounded-xl border">
            {sessions.data.map((session) => (
              <li key={session.id} className="flex flex-wrap items-center gap-3 p-3">
                <Desktop className="size-5 text-muted-foreground" aria-hidden />
                <div className="min-w-0 flex-1">
                  <p className="flex items-center gap-2 text-sm font-medium">{session.device}{session.is_current && <SoftBadge tone="success">This device</SoftBadge>}</p>
                  <p className="text-xs text-muted-foreground">Last active {formatDateTime(session.last_active_at)} · signed in {formatDateTime(session.created_at)}</p>
                </div>
                {session.is_current ? (
                  <Button variant="outline" size="sm" icon={<SignOut />} loading={signOut.isPending} onClick={() => signOut.mutate()}>Sign out</Button>
                ) : (
                  <Button variant="outline" size="sm" loading={revoke.isPending && revoke.variables === session.id} onClick={() => revoke.mutate(session.id, { onError: (e) => toast.error(errorMessage(e)) })}>Sign out this device</Button>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="danger" className="space-y-3">
        <h2 id="danger" className="text-lg font-semibold">Delete account</h2>
        <p className="max-w-prose text-sm text-muted-foreground">Your account is scheduled for deletion and removed after a grace period. You cannot delete it while you own a workspace; transfer or delete those first.</p>
        <Button variant="destructive" icon={<Trash />} onClick={() => setConfirmDelete(true)}>Delete my account</Button>
        <ConfirmDialog
          open={confirmDelete}
          onOpenChange={setConfirmDelete}
          title="Delete your account?"
          description="You will be signed out everywhere and your account is scheduled for deletion."
          confirmLabel="Delete account"
          destructive
          onConfirm={() =>
            deleteAccount.mutate(undefined, {
              onSuccess: (message) => {
                toast.success(message)
                window.location.assign('/')
              },
              onError: (e) => toast.error(errorMessage(e)),
            })
          }
        />
      </section>
    </div>
  )
}
