import { useNavigate } from '@tanstack/react-router'
import { useCallback, useEffect, useState } from 'react'

import type { NavItem, UserMenuItem } from '@/components/layout/app-shell'
import { Shortcut } from '@/components/ui/kbd'
import { CommandDialog, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList, CommandShortcut } from '@/components/ui/command'
import { Keyboard, MagnifyingGlass, User } from '@/icons'

const GO_KEYS: Record<string, string> = { Dashboard: 'G D', Tickets: 'G T', Knowledge: 'G K', Members: 'G M' }

/** Opens on Win+K or Ctrl+K, even while typing, like documentation search. */
function useSearchHotkey(toggle: () => void) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key.toLowerCase() === 'k' && (e.metaKey || e.ctrlKey) && !e.altKey) {
        e.preventDefault()
        toggle()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [toggle])
}

/**
 * Top-bar search: a field-shaped button that opens a palette to jump to any page or open the shortcuts list.
 * It searches pages and actions only, not ticket or article content.
 */
export function AppSearch({ nav, userMenu, onShowShortcuts }: { nav: NavItem[]; userMenu: UserMenuItem[]; onShowShortcuts: () => void }) {
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()
  useSearchHotkey(useCallback(() => setOpen((v) => !v), []))
  const go = (href: string) => {
    setOpen(false)
    void navigate({ to: href as never })
  }
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Search"
        className="flex h-8 w-8 shrink-0 items-center justify-center gap-2 rounded-lg border border-border bg-muted/40 text-sm text-muted-foreground outline-none transition-colors hover:border-[color-mix(in_oklch,var(--border),var(--foreground)_18%)] hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring/50 pointer-coarse:size-11 md:w-64 md:justify-start md:px-2.5 lg:w-80"
      >
        <MagnifyingGlass className="size-4 shrink-0" aria-hidden />
        <span className="hidden flex-1 truncate text-left md:inline">Search or jump to…</span>
        <Shortcut keys="Mod+K" className="hidden md:inline-flex" />
      </button>
      <CommandDialog open={open} onOpenChange={setOpen} title="Search" description="Jump to a page or open the keyboard shortcuts.">
        <CommandInput placeholder="Search pages…" />
        <CommandList>
          <CommandEmpty>No results.</CommandEmpty>
          <CommandGroup heading="Go to">
            {nav.map(({ label, href, icon: Icon, disabledReason }) => (
              <CommandItem key={href} value={label} disabled={!!disabledReason} onSelect={() => go(href)}>
                <Icon />{label}{GO_KEYS[label] && <CommandShortcut keys={GO_KEYS[label]} />}
              </CommandItem>
            ))}
            {userMenu.map(({ label, href, icon: Icon }) => (
              <CommandItem key={href} value={label} onSelect={() => go(href)}><Icon />{label}</CommandItem>
            ))}
          </CommandGroup>
          {nav.some((item) => item.label === 'Tickets') && (
            <CommandGroup heading="Quick views">
              <CommandItem value="My tickets" onSelect={() => { setOpen(false); void navigate({ to: nav.find((item) => item.label === 'Tickets')!.href as never, search: { assignee: 'me' } as never }) }}><User />My tickets</CommandItem>
            </CommandGroup>
          )}
          <CommandGroup heading="Help">
            <CommandItem value="Keyboard shortcuts" onSelect={() => { setOpen(false); onShowShortcuts() }}>
              <Keyboard />Keyboard shortcuts<CommandShortcut keys="?" />
            </CommandItem>
          </CommandGroup>
        </CommandList>
      </CommandDialog>
    </>
  )
}
