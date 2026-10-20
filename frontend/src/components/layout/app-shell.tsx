import { useRef, useState, type ComponentType, type ReactNode } from "react"
import { Logo } from "@/components/patterns/logo"
import { ThemeToggle } from "@/components/patterns/theme-toggle"
import { UserAvatar } from "@/components/patterns/user-avatar"
import { Button } from "@/components/ui/button"
import { DropdownMenu, DropdownMenuContent, DropdownMenuGroup, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { Bell, List, SidebarSimple, SignOut } from "@/icons"
import type { IconProps } from "@/icons"
import { useIconMotion } from "@/motion/icon-motion"
import { cn } from "@/lib/utils"

export type NavItem = { label: string; href: string; icon: ComponentType<IconProps>; active?: boolean; count?: number }
export type ShellUser = { name: string; email?: string }

function NavLink({ item, expanded }: { item: NavItem; expanded: boolean }) {
  const { icon: Icon, label, href, active, count } = item
  return (
    <a
      href={href}
      aria-current={active ? "page" : undefined}
      aria-label={expanded ? undefined : label}
      title={expanded ? undefined : label}
      data-icon-motion="lift"
      className={cn(
        "flex h-8 items-center gap-2 rounded-md px-2 text-sm text-muted-foreground transition-colors outline-none hover:bg-sidebar-accent hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50 pointer-coarse:h-11",
        active && "bg-sidebar-accent font-medium text-foreground",
        !expanded && "justify-center px-0",
      )}
    >
      <Icon weight={active ? "fill" : "regular"} className="size-4 shrink-0" aria-hidden />
      {expanded && <span className="truncate">{label}</span>}
      {expanded && count ? <span className="ml-auto text-xs tabular-nums text-muted-foreground">{count}</span> : null}
    </a>
  )
}

/**
 * Flat app frame: icon rail that expands to labels, hairline top bar with breadcrumb, actions and account.
 * Routing-agnostic: nav items are plain anchors; swap `NavLink` for the router link when pages exist.
 */
export function AppShell({ nav, breadcrumb, actions, user, onSignOut, children }: {
  nav: NavItem[]
  breadcrumb: ReactNode
  /** Extra top-bar controls before the theme toggle (search, notifications). */
  actions?: ReactNode
  user: ShellUser
  onSignOut?: () => void
  children: ReactNode
}) {
  const [expanded, setExpanded] = useState(false)
  const root = useRef<HTMLDivElement>(null)
  useIconMotion(root)
  return (
    <div ref={root} className="flex min-h-screen">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:rounded-md focus:bg-background focus:px-3 focus:py-2 focus:text-sm focus:ring-3 focus:ring-ring/50">Skip to content</a>
      <aside aria-label="Sidebar" className={cn("sticky top-0 hidden h-screen shrink-0 flex-col gap-1 border-r bg-sidebar p-2 transition-[width] duration-200 ease-out md:flex", expanded ? "w-56" : "w-14")}>
        <a href="/" aria-label="ResolveAI home" className="mb-2 flex h-9 items-center rounded-md px-1.5 outline-none focus-visible:ring-3 focus-visible:ring-ring/50">
          <Logo mark={!expanded} />
        </a>
        <nav aria-label="Main" className="space-y-0.5">
          {nav.map((item) => <NavLink key={item.label} item={item} expanded={expanded} />)}
        </nav>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex h-12 items-center gap-2 border-b bg-background px-3 md:px-4">
          <div className="md:hidden">
            <DropdownMenu>
              <DropdownMenuTrigger render={<Button variant="outline" size="icon" label="Menu"><List /></Button>} />
              <DropdownMenuContent className="w-56">
                <DropdownMenuGroup>
                  {nav.map(({ label, href, icon: Icon }) => (
                    <DropdownMenuItem key={label} render={<a href={href} />}><Icon />{label}</DropdownMenuItem>
                  ))}
                </DropdownMenuGroup>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
          <Button variant="ghost" size="icon" label={expanded ? "Collapse sidebar" : "Expand sidebar"} className="hidden md:inline-flex" onClick={() => setExpanded(!expanded)} aria-expanded={expanded} data-icon-motion="turn">
            <SidebarSimple />
          </Button>
          <span aria-hidden className="hidden h-4 w-px bg-border md:block" />
          <div className="min-w-0 flex-1 text-sm">{breadcrumb}</div>
          <div className="flex items-center gap-1.5">
            {actions}
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
