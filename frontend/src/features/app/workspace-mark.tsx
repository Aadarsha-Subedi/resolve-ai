import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { initials } from '@/lib/format'

/** A workspace's logo, or its initials on a neutral tile. Decorative: the name is written beside it. */
export function WorkspaceMark({ workspace, size = 'sm' }: { workspace: { name: string; logo_url: string | null }; size?: 'sm' | 'default' | 'lg' }) {
  return (
    <Avatar size={size} className="rounded-md after:rounded-md" aria-hidden>
      {workspace.logo_url && <AvatarImage src={workspace.logo_url} alt="" className="rounded-md" />}
      <AvatarFallback className="rounded-md">{initials(workspace.name)}</AvatarFallback>
    </Avatar>
  )
}
