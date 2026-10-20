import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { initials } from "@/lib/format"

/** A person's picture, with initials when there is none. Decorative: the name is always written next to it. */
export function UserAvatar({ name, src, size = "default", className }: { name: string; src?: string | null; size?: "default" | "sm" | "lg"; className?: string }) {
  return (
    <Avatar size={size} className={className} aria-hidden>
      {src && <AvatarImage src={src} alt="" />}
      <AvatarFallback>{initials(name)}</AvatarFallback>
    </Avatar>
  )
}
