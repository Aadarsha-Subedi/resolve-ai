import { AppShell, type NavItem } from "@/components/layout/app-shell"
import { PageHeader } from "@/components/patterns/page-header"
import { StatCard } from "@/components/patterns/stat-card"
import { Button } from "@/components/ui/button"
import { BookOpen, ChartBar, Gear, Tray, MagnifyingGlass, Plus, Ticket, Users } from "@/icons"

const NAV: NavItem[] = [
  { label: "Dashboard", href: "#", icon: ChartBar },
  { label: "Tickets", href: "#", icon: Ticket, active: true, count: 8 },
  { label: "Tray", href: "#", icon: Tray },
  { label: "Knowledge base", href: "#", icon: BookOpen },
  { label: "Members", href: "#", icon: Users },
  { label: "Settings", href: "#", icon: Gear },
]

/** The app frame on its own, empty, so the shell can be judged at full viewport. */
export function FramePreview() {
  return (
    <AppShell
      nav={NAV}
      user={{ name: "Jason Duong", email: "jason@acme.test" }}
      search={<Button variant="outline" size="sm" icon={<MagnifyingGlass />} className="text-muted-foreground">Search or jump to…</Button>}
    >
      <div className="space-y-6">
        <PageHeader title="Tickets" actions={<Button icon={<Plus weight="bold" />} data-icon-motion="spin">New Ticket</Button>} />
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Total tickets" value={20} icon={<Ticket className="size-3.5" />} trend={{ change: 3, percent: "17.6%", good: false }} />
          <StatCard label="Open" value={8} icon={<Tray className="size-3.5" />} trend={{ change: -2, percent: "20%", good: true }} />
          <StatCard label="Pending" value={5} />
          <StatCard label="Resolved" value={4} />
        </div>
      </div>
    </AppShell>
  )
}
