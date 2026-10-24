import { UserAvatar } from "@/components/patterns/user-avatar"
import { UserCircleDashed } from "@/icons"

/** Avatar plus name, or a muted "Unassigned". */
export function Assignee({ name, src }: { name?: string | null; src?: string | null }) {
  if (!name) {
    return (
      <span className="inline-flex items-center gap-2 text-muted-foreground">
        <UserCircleDashed className="size-5" aria-hidden />
        Unassigned
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-2">
      <UserAvatar name={name} src={src} size="sm" />
      {name}
    </span>
  )
}
