import { Navigate, Outlet, useParams } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'

import { AppShell, type NavItem, type UserMenuItem } from '@/components/layout/app-shell'
import { ShortcutsDialog, useShortcutsHotkey } from '@/components/patterns/shortcuts-menu'
import { Skeleton } from '@/components/ui/skeleton'
import { currentUserQuery } from '@/features/auth/api'
import { useSignOut } from '@/features/account/api'
import { AppSearch } from '@/features/app/app-search'
import { useGoShortcuts } from '@/features/app/go-shortcuts'
import { ErrorPanel } from '@/features/app/page-states'
import { WorkspaceSwitcher } from '@/features/app/workspace-switcher'
import { getLastWorkspace, useWorkspaces } from '@/features/workspaces/api'
import { ClockCounterClockwise, EnvelopeSimple, Gear, Notebook, Robot, SquaresFour, Ticket, UserCircle, UsersThree } from '@/icons'

const USER_MENU: UserMenuItem[] = [
  { label: 'Email (Gmail)', href: '/app/email', icon: EnvelopeSimple },
  { label: 'Account', href: '/app/account', icon: UserCircle },
]

/** Placeholder frame shown while the session and workspace list load, so no route waits on the network. */
function BootSkeleton() {
  return (
    <div className="flex min-h-screen" aria-busy="true" aria-label="Loading">
      <aside className="hidden w-14 shrink-0 flex-col gap-3 border-r bg-sidebar p-2 md:flex">
        <Skeleton className="size-9" />
        {Array.from({ length: 6 }, (_, i) => <Skeleton key={i} className="h-8 w-full" />)}
      </aside>
      <div className="flex-1">
        <div className="flex h-12 items-center gap-3 border-b px-4"><Skeleton className="h-8 w-40" /><Skeleton className="ml-auto size-8 rounded-full" /></div>
        <div className="space-y-4 p-6"><Skeleton className="h-8 w-56" /><Skeleton className="h-40 w-full" /></div>
      </div>
    </div>
  )
}

export function AppLayout() {
  const user = useQuery(currentUserQuery)
  const workspaces = useWorkspaces()
  const params = useParams({ strict: false }) as { ws?: string }
  const [shortcutsOpen, setShortcutsOpen] = useState(false)
  useShortcutsHotkey(() => setShortcutsOpen(true))
  const signOut = useSignOut()

  const currentId = params.ws ?? (workspaces.data?.some((w) => w.id === getLastWorkspace()) ? getLastWorkspace()! : workspaces.data?.[0]?.id)
  const current = workspaces.data?.find((w) => w.id === currentId)
  useGoShortcuts(current?.id)

  const nav = useMemo<NavItem[]>(() => {
    if (!current) return []
    const base = `/app/${current.id}`
    return [
      { label: 'Dashboard', href: base, icon: SquaresFour },
      { label: 'Tickets', href: `${base}/tickets`, icon: Ticket },
      { label: 'Knowledge', href: `${base}/knowledge`, icon: Notebook },
      { label: 'Ask', href: `${base}/ask`, icon: Robot },
      { label: 'Members', href: `${base}/members`, icon: UsersThree },
      { label: 'Audit log', href: `${base}/audit`, icon: ClockCounterClockwise, disabledReason: current.role === 'owner' ? undefined : 'Only the workspace owner can read the audit log.' },
      { label: 'Settings', href: `${base}/settings`, icon: Gear },
    ]
  }, [current])

  if (user.isPending) return <BootSkeleton />
  if (user.error) return <div className="p-6"><ErrorPanel error={user.error} onRetry={() => void user.refetch()} title="Could not load your account" /></div>
  if (!user.data) return <Navigate to="/login" />

  return (
    <AppShell
      nav={nav}
      leading={<WorkspaceSwitcher workspaces={workspaces.data} currentId={currentId} />}
      search={<AppSearch nav={nav} userMenu={USER_MENU} onShowShortcuts={() => setShortcutsOpen(true)} />}
      user={{ name: user.data.display_name, email: user.data.email }}
      userMenu={USER_MENU}
      onSignOut={() => signOut.mutate()}
    >
      <Outlet />
      <ShortcutsDialog open={shortcutsOpen} onOpenChange={setShortcutsOpen} />
    </AppShell>
  )
}
