import { cloneElement, isValidElement, type ReactElement, type ReactNode } from "react"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"

/**
 * Permission gate for an action. Allowed: renders the child untouched. Not allowed: the child is
 * disabled and hovering or focusing it shows `reason` in a tooltip (no helper text under the button).
 * The wrapper span receives the pointer events, because a disabled button swallows them.
 */
export function Restricted({ reason, children }: { reason?: string | null | false; children: ReactNode }) {
  if (!reason) return <>{children}</>
  const disabledChild = isValidElement(children)
    ? cloneElement(children as ReactElement<{ disabled?: boolean }>, { disabled: true })
    : children
  return (
    <Tooltip>
      <TooltipTrigger render={<span tabIndex={0} className="inline-flex rounded-full outline-none focus-visible:ring-3 focus-visible:ring-ring/50" />}>
        {disabledChild}
      </TooltipTrigger>
      <TooltipContent>{reason}</TooltipContent>
    </Tooltip>
  )
}
