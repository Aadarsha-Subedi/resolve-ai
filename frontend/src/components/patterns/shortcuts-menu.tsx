import { useEffect } from "react"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Shortcut } from "@/components/ui/kbd"

export type ShortcutGroup = { title: string; items: { label: string; keys: string }[] }

/** What the shortcuts dialog lists. Only shortcuts that are actually wired belong here. */
export const APP_SHORTCUTS: ShortcutGroup[] = [
  { title: "Anywhere", items: [{ label: "Search and jump to a page", keys: "Meta+K, Ctrl+K" }, { label: "Open this list", keys: "?" }] },
  { title: "Go to", items: [{ label: "Dashboard", keys: "G D" }, { label: "Tickets", keys: "G T" }, { label: "Knowledge", keys: "G K" }, { label: "Members", keys: "G M" }] },
]

const isTyping = (target: EventTarget | null) => {
  const el = target as HTMLElement | null
  return !!el && (el.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName))
}

/** Calls `open` on `?`, ignored while typing. Search has its own Win+K / Ctrl+K hotkey. */
export function useShortcutsHotkey(open: () => void) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "?" && !e.metaKey && !e.ctrlKey && !e.altKey && !isTyping(e.target)) {
        e.preventDefault()
        open()
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [open])
}

/** The dialog body: key caps next to what they do, grouped. */
export function ShortcutsList({ groups = APP_SHORTCUTS }: { groups?: ShortcutGroup[] }) {
  return (
    <div className="space-y-5">
      {groups.map((group) => (
        <section key={group.title} aria-label={group.title} className="space-y-1">
          <h3 className="text-xs font-medium text-muted-foreground">{group.title}</h3>
          <ul>
            {group.items.map((item) => (
              <li key={`${item.label}${item.keys}`} className="flex h-9 items-center justify-between gap-4 border-b border-border/60 last:border-0">
                <span className="text-sm">{item.label}</span>
                <Shortcut keys={item.keys} />
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  )
}

/** The Keyboard shortcuts dialog. The owner holds `open` so the search palette can open it too. */
export function ShortcutsDialog({ open, onOpenChange, groups }: { open: boolean; onOpenChange: (open: boolean) => void; groups?: ShortcutGroup[] }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Keyboard shortcuts</DialogTitle>
          <DialogDescription>Press ? anywhere to open this list.</DialogDescription>
        </DialogHeader>
        <ShortcutsList groups={groups} />
      </DialogContent>
    </Dialog>
  )
}
