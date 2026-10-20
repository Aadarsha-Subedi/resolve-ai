import { useEffect, useState } from "react"
import { toast } from "sonner"
import { ConfirmDialog } from "@/components/patterns/confirm-dialog"
import { Button } from "@/components/ui/button"
import { CommandDialog, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList, CommandShortcut } from "@/components/ui/command"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { DropdownMenu, DropdownMenuContent, DropdownMenuGroup, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuShortcut, DropdownMenuSub, DropdownMenuSubContent, DropdownMenuSubTrigger, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card"
import { Input } from "@/components/ui/input"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Shortcut } from "@/components/ui/kbd"
import { Textarea } from "@/components/ui/textarea"
import { Assignee } from "@/components/patterns/assignee"
import { STATUS_OPTIONS } from "@/components/patterns/ticket-meta"
import { Keyboard, ArrowsLeftRight, CaretDown, CheckSquare, Copy, DotsThree, Funnel, MagnifyingGlass, PencilSimple, Plus, Trash, UserPlus } from "@/icons"
import { Section, Specimen } from "../section"

const SHORTCUTS = [
  { group: "General", items: [["Command palette", "Mod+K"], ["Keyboard shortcuts", "?"], ["Search tickets", "/"]] },
  { group: "Tickets", items: [["New ticket", "C"], ["Reply", "R"], ["Go to my tickets", "G T"], ["Resolve", "Mod+Shift+Enter"]] },
] as const

export function Menus() {
  const [cmd, setCmd] = useState(false)
  const [confirm, setConfirm] = useState(false)
  useEffect(() => {
    const on = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setCmd((v) => !v) }
    }
    window.addEventListener("keydown", on)
    return () => window.removeEventListener("keydown", on)
  }, [])
  return (
    <Section id="menus" title="Menus and overlays" intro="Action menus, command palette, popovers and dialogs. A modal appears only where focus must be protected; everything else is a popover.">
      <div className="grid gap-10 lg:grid-cols-2">
        <Specimen title="Action menu" note="Row actions with submenu, shortcuts and a destructive item">
          <DropdownMenu>
            <DropdownMenuTrigger render={<Button variant="outline" iconEnd={<CaretDown />} icon={<DotsThree weight="bold" />}>Actions</Button>} />
            <DropdownMenuContent className="w-56">
              <DropdownMenuGroup>
                <DropdownMenuLabel>Ticket #-001</DropdownMenuLabel>
                <DropdownMenuItem><PencilSimple /> Reply <DropdownMenuShortcut keys="R" /></DropdownMenuItem>
                <DropdownMenuItem><Copy /> Copy link</DropdownMenuItem>
                <DropdownMenuSub>
                  <DropdownMenuSubTrigger><ArrowsLeftRight /> Set status</DropdownMenuSubTrigger>
                  <DropdownMenuSubContent>
                    {STATUS_OPTIONS.map((s) => <DropdownMenuItem key={s.value}>{s.label}</DropdownMenuItem>)}
                  </DropdownMenuSubContent>
                </DropdownMenuSub>
                <DropdownMenuItem><UserPlus /> Assign…</DropdownMenuItem>
              </DropdownMenuGroup>
              <DropdownMenuSeparator />
              <DropdownMenuItem variant="destructive"><Trash /> Delete</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </Specimen>
        <Specimen title="Command palette" note="Cmd/Ctrl + K">
          <Button variant="outline" icon={<MagnifyingGlass />} onClick={() => setCmd(true)} className="text-muted-foreground">Search or jump to… <Shortcut keys="Mod+K" className="ml-6" /></Button>
          <CommandDialog open={cmd} onOpenChange={setCmd} title="Command palette" description="Jump to a screen or run an action.">
            <CommandInput placeholder="Type a command or search…" />
            <CommandList>
              <CommandEmpty>No results.</CommandEmpty>
              <CommandGroup heading="Actions">
                <CommandItem><Plus /> New ticket <CommandShortcut keys="C" /></CommandItem>
                <CommandItem><PencilSimple /> Reply to ticket <CommandShortcut keys="R" /></CommandItem>
                <CommandItem><Funnel /> Filter by status <CommandShortcut keys="F" /></CommandItem>
              </CommandGroup>
              <CommandGroup heading="Go to">
                <CommandItem><CheckSquare /> My tickets <CommandShortcut keys="G T" /></CommandItem>
                <CommandItem><Keyboard /> Keyboard shortcuts <CommandShortcut keys="?" /></CommandItem>
              </CommandGroup>
            </CommandList>
          </CommandDialog>
        </Specimen>
        <Specimen title="Keyboard shortcuts" note="Plain dialog surface, groups spaced apart, keys as key caps. Press ? anywhere to open it.">
          <Dialog>
            <DialogTrigger render={<Button variant="outline" icon={<Keyboard />}>Keyboard shortcuts</Button>} />
            <DialogContent className="sm:max-w-md">
              <DialogHeader><DialogTitle>Keyboard shortcuts</DialogTitle><DialogDescription>Work the queue without leaving the keyboard.</DialogDescription></DialogHeader>
              <div className="flex flex-col gap-6 py-2">
                {SHORTCUTS.map((g) => (
                  <section key={g.group} aria-label={g.group} className="flex flex-col gap-1">
                    <h3 className="text-xs font-medium text-muted-foreground">{g.group}</h3>
                    <ul>
                      {g.items.map(([label, keys]) => (
                        <li key={label} className="flex h-9 items-center justify-between text-sm">
                          {label}
                          <Shortcut keys={keys} />
                        </li>
                      ))}
                    </ul>
                  </section>
                ))}
              </div>
            </DialogContent>
          </Dialog>
        </Specimen>
        <Specimen title="Popover and hover card">
          <div className="flex flex-wrap items-center gap-2">
            <Popover>
              <PopoverTrigger render={<Button variant="outline" icon={<Funnel />}>Filters</Button>} />
              <PopoverContent className="w-64"><p className="text-sm font-medium">Quick filters</p><p className="mt-1 text-xs text-muted-foreground">Small, non-blocking surface anchored to its button.</p></PopoverContent>
            </Popover>
            <HoverCard>
              <HoverCardTrigger render={<a href="#menus" className="text-sm underline underline-offset-4">Jason Duong</a>} />
              <HoverCardContent className="w-60"><Assignee name="Jason Duong" /><p className="mt-2 text-xs text-muted-foreground">12 open tickets, replies within 2 hours on average.</p></HoverCardContent>
            </HoverCard>
          </div>
        </Specimen>
        <Specimen title="Dialogs" note="Dialog for forms that need focus, confirm dialog for destructive steps">
          <div className="flex flex-wrap gap-2">
            <Dialog>
              <DialogTrigger render={<Button icon={<Plus weight="bold" />}>New Ticket</Button>} />
              <DialogContent className="sm:max-w-lg">
                <DialogHeader><DialogTitle>New ticket</DialogTitle><DialogDescription>Centered, focused, dismissed with Esc.</DialogDescription></DialogHeader>
                <div className="space-y-3"><Input placeholder="Subject" autoFocus /><Textarea placeholder="Describe the problem…" /></div>
                <DialogFooter><Button icon={<Plus weight="bold" />} onClick={() => toast.success("Ticket created")}>Create ticket</Button></DialogFooter>
              </DialogContent>
            </Dialog>
            <Button variant="destructive" icon={<Trash />} onClick={() => setConfirm(true)}>Delete ticket</Button>
            <ConfirmDialog open={confirm} onOpenChange={setConfirm} title="Delete this ticket?" description="The conversation and its notes are removed for everyone. This cannot be undone." confirmLabel="Delete ticket" destructive onConfirm={() => toast.success("Ticket deleted")} />
          </div>
        </Specimen>
      </div>
    </Section>
  )
}
