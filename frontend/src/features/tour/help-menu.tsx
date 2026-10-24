import { Button } from '@/components/ui/button'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { useTour } from '@/features/tour/tour'
import { Keyboard, Question, Compass } from '@/icons'

/** Top-bar Help menu: replay the tour for the page in view, or list the keyboard shortcuts. */
export function HelpMenu({ onShowShortcuts }: { onShowShortcuts: () => void }) {
  const { page, replay } = useTour()
  return (
    <DropdownMenu>
      <DropdownMenuTrigger render={<Button variant="ghost" size="icon" label="Help"><Question /></Button>} />
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuItem disabled={!page} onClick={replay}><Compass />Tour this page</DropdownMenuItem>
        <DropdownMenuItem onClick={onShowShortcuts}><Keyboard />Keyboard shortcuts</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
