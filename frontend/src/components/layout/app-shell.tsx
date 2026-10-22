import { Link, useRouterState } from "@tanstack/react-router"
import { useRef, useState, type ComponentType, type ReactNode } from "react"
import { Logo } from "@/components/patterns/logo"
import { ThemeToggle } from "@/components/patterns/theme-toggle"
import { UserAvatar } from "@/components/patterns/user-avatar"
import { Button } from "@/components/ui/button"
import { DropdownMenu, DropdownMenuContent, DropdownMenuGroup, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { Bell, List, SidebarSimple, SignOut } from "@/icons"
import type { IconProps } from "@/icons"
import { useIconMotion } from "@/motion/icon-motion"
import { cn } from "@/lib/utils"

export type NavItem = {
  label: string
  href: string
  icon: ComponentType<IconProps>
  /** Marks the item current; when omitted the router location decides (prefix match on `href`). */
  active?: boolean
  count?: number
  /** Item stays visible but cannot be used; the reason shows in a tooltip. */
  disabledReason?: string
}
export type ShellUser = { name: string; email?: string }
export type UserMenuItem = { label: string; href: string; icon: ComponentType<IconProps> }

function useIsActive(item: NavItem) {
  const pathname = useRouterState({ select: (s) => s.location.pathname })
  if (item.active !== undefined) return item.active
  // A workspace's dashboard lives at its root, so it must match exactly.
  return pathname === item.href || (pathname.startsWith(`${item.href}/`) && !/^\/app\/[^/]+$/.test(item.href))
}

const linkClass = (active: boolean, expanded: boolean, disabled?: boolean) =>
  cn(
    "flex h-8 items-center gap-2 rounded-md px-2 text-sm text-muted-foreground transition-colors outline-none hover:bg-sidebar-accent hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50 pointer-coarse:h-11",
    active && "bg-sidebar-accent font-medium text-foreground",
    !expanded && "justify-center px-0",
    disabled && "cursor-not-allowed opacity-50 hover:bg-transparent hover:text-muted-foreground",
  )

function NavLink({ item, expanded }: { item: NavItem; expanded: boolean }) {
  const { icon: Icon, label, href, count, disabledReason } = item
  const active = useIsActive(item)
  const content = (
    <>
      <Icon weight={active ? "fill" : "regular"} className="size-4 shrink-0" aria-hidden />
      {expanded && <span className="truncate">{label}</span>}
      {expanded && count ? <span className="ml-auto text-xs tabular-nums text-muted-foreground">{count}</span> : null}
    </>
  )
  if (disabledReason) {
    return (
      <Tooltip>
        <TooltipTrigger render={<span role="link" aria-disabled="true" tabIndex={0} aria-label={`${label} (unavailable)`} data-icon-motion="lift" className={linkClass(false, expanded, true)} />}>
          {content}
        </TooltipTrigger>
        <TooltipContent side="right">{disabledReason}</TooltipContent>
      </Tooltip>
    )
  }
  return (
    <Link to={href as never} aria-current={active ? "page" : undefined} aria-label={expanded ? undefined : label} title={expanded ? undefined : label} data-icon-motion="lift" className={linkClass(active, expanded)}>
      {content}
    </Link>
  )
}

/**
 * Flat app frame: icon rail that expands to labels (click empty rail space or the toggle at its foot), hairline
 * top bar with workspace switcher and search on the left, theme toggle and account menu on the right. Nav items
 * are router links; an item with `disabledReason` stays visible and explains itself.
 */
export function AppShell({ nav, leading, search, user, userMenu, onSignOut, children }: {
  nav: NavItem[]
  /** Top-bar control at the left edge (the workspace switcher). */
  leading?: ReactNode
  /** Top-bar search, after the workspace switcher. */
  search?: ReactNode
  user: ShellUser
  /** Extra account-menu entries above "Sign out" (Email, Account). */
  userMenu?: UserMenuItem[]
  onSignOut?: () => void
  children: ReactNode
}) {
  const [expanded, setExpanded] = useState(false)
  const root = useRef<HTMLDivElement>(null)
  useIconMotion(root)
  return (
    <div ref={root} className="flex min-h-screen">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:rounded-md focus:bg-background focus:px-3 focus:py-2 focus:text-sm focus:ring-3 focus:ring-ring/50">Skip to content</a>
      {/* The collapsed rail is one big expand target; links and buttons keep their own behaviour. The foot toggle is the keyboard path. */}
      <aside
        aria-label="Sidebar"
        onClick={(e) => { if (!expanded && !(e.target as HTMLElement).closest("a, button, [role=link]")) setExpanded(true) }}
        className={cn("sticky top-0 hidden h-screen shrink-0 flex-col gap-1 border-r bg-sidebar p-2 transition-[width] duration-200 ease-out motion-reduce:transition-none md:flex", expanded ? "w-56" : "w-14 cursor-e-resize")}
      >
        <Link to="/app" aria-label="ResolveAI home" className="mb-2 flex h-9 items-center rounded-md px-1.5 outline-none focus-visible:ring-3 focus-visible:ring-ring/50">
          <Logo mark={!expanded} />
        </Link>
        <nav aria-label="Main" className="space-y-0.5">
          {nav.map((item) => <NavLink key={item.label} item={item} expanded={expanded} />)}
        </nav>
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          aria-expanded={expanded}
          aria-label={expanded ? "Collapse sidebar" : "Expand sidebar"}
          title={expanded ? undefined : "Expand sidebar"}
          data-icon-motion="turn"
          className={cn(linkClass(false, expanded), "mt-auto w-full cursor-pointer")}
        >
          <SidebarSimple className="size-4 shrink-0" aria-hidden />
          {expanded && <span className="truncate">Collapse</span>}
        </button>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex h-12 items-center gap-2 border-b bg-background px-3 md:px-4">
          <div className="md:hidden">
            <DropdownMenu>
              <DropdownMenuTrigger render={<Button variant="ghost" size="icon" label="Menu"><List /></Button>} />
              <DropdownMenuContent className="w-56">
                <DropdownMenuGroup>
                  {nav.map(({ label, href, icon: Icon, disabledReason }) => (
                    <DropdownMenuItem key={label} disabled={!!disabledReason} render={<Link to={href as never} />}><Icon />{label}</DropdownMenuItem>
                  ))}
                </DropdownMenuGroup>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
          {leading}
          {search}
          <div className="ml-auto flex items-center gap-1">
            <ThemeToggle />
            <DropdownMenu>
              <DropdownMenuTrigger render={<Button variant="ghost" size="icon" label="Account"><UserAvatar name={user.name} size="sm" /></Button>} />
              <DropdownMenuContent align="end" className="w-60">
                <DropdownMenuGroup>
                  <DropdownMenuLabel className="flex flex-col gap-0.5">
                    <span className="truncate text-sm font-medium text-foreground">{user.name}</span>
                    {user.email && <span className="truncate text-xs font-normal text-muted-foreground">{user.email}</span>}
                  </DropdownMenuLabel>
                </DropdownMenuGroup>
                <DropdownMenuSeparator />
                {userMenu?.map(({ label, href, icon: Icon }) => (
                  <DropdownMenuItem key={label} render={<Link to={href as never} />}><Icon />{label}</DropdownMenuItem>
                ))}
                {userMenu?.length ? <DropdownMenuSeparator /> : null}
                <DropdownMenuItem onClick={onSignOut}><SignOut />Sign out</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>
        <main id="main" tabIndex={-1} className="flex-1 px-4 py-6 outline-none md:px-6">{children}</main>
      </div>
    </div>
  )
}

/** Notification bell for the top bar; the dot appears only when there is something unread. */
export function BellButton({ unread }: { unread?: boolean }) {
  return (
    <Button variant="ghost" size="icon" label={unread ? "Notifications, unread" : "Notifications"} data-icon-motion="swing" className="relative">
      <Bell />
      {unread && <span aria-hidden className="absolute top-1.5 right-1.5 size-1.5 rounded-full bg-primary ring-2 ring-background" />}
    </Button>
  )
}
