import { Button } from "@/components/ui/button"
import { GoogleLogo } from "@/icons"
import { googleStartUrl } from "@/features/auth/api"

/** Both sign-up and sign-in are the backend's Google flow: a full-page redirect, so this is a link and not a click handler. */
export function GoogleButton({ children = "Continue with Google", size, className, remember = false }: { children?: string; size?: "default" | "lg"; className?: string; remember?: boolean }) {
  return (
    <Button render={<a href={googleStartUrl({ remember })} />} icon={<GoogleLogo weight="bold" />} size={size} className={className}>
      {children}
    </Button>
  )
}
