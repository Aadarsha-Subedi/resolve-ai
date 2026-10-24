import { Link, useNavigate } from '@tanstack/react-router'

import { Button } from '@/components/ui/button'
import { DropdownMenu, DropdownMenuContent, DropdownMenuGroup, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { Check, CaretUpDown, EnvelopeSimple, Plus } from '@/icons'
import { Skeleton } from '@/components/ui/skeleton'
import { WorkspaceMark } from '@/features/app/workspace-mark'
import type { Workspace } from '@/lib/types'

/** Top-bar dropdown: the current workspace, the others you belong to, create, invitations. */
export function WorkspaceSwitcher({ workspaces, currentId }: { workspaces: Workspace[] | undefined; currentId: string | undefined }) {
  const navigate = useNavigate()
  const current = workspaces?.find((w) => w.id === currentId)
  if (!workspaces) return <Skeleton className="h-8 w-36" />
  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button variant="ghost" size="sm" slide={false} className="max-w-56 gap-2 px-2" aria-label="Switch workspace">
            {current ? <WorkspaceMark workspace={current} /> : null}
            <span className="truncate">{current?.name ?? 'Choose workspace'}</span>
            <CaretUpDown className="text-muted-foreground" />
          </Button>
        }
      />
      <DropdownMenuContent align="start" className="w-64">
        <DropdownMenuGroup>
          <DropdownMenuLabel>Workspaces</DropdownMenuLabel>
          {workspaces.map((w) => (
            <DropdownMenuItem key={w.id} onClick={() => void navigate({ to: `/app/${w.id}` as never })}>
              <WorkspaceMark workspace={w} />
              <span className="min-w-0 flex-1 truncate">{w.name}</span>
              <span className="text-xs text-muted-foreground">{w.role === 'owner' ? 'Owner' : 'Member'}</span>
              {w.id === currentId && <Check weight="bold" aria-label="Current" />}
            </DropdownMenuItem>
          ))}
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem render={<Link to="/app/new" />}><Plus />New workspace</DropdownMenuItem>
        <DropdownMenuItem render={<Link to="/app/invitations" />}><EnvelopeSimple />Invitations</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
