import { Button as ButtonPrimitive } from "@base-ui/react/button"
import type { ReactNode } from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"
import { Spinner } from "@/components/ui/spinner"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"

/**
 * Rounded-lg buttons with a premium finish on the default variant (top highlight, soft shadow); no outline border on default or outline variants.
 * Leading icons ease up and trailing icons nudge right on hover; icon-only buttons scale slightly. CSS only,
 * and reduced motion drops the movement.
 */
const buttonVariants = cva(
  `group/button relative inline-flex shrink-0 pointer-coarse:min-h-11 cursor-pointer items-center justify-center rounded-lg border border-transparent bg-clip-padding text-sm font-medium whitespace-nowrap transition-[background-color,box-shadow,border-color] duration-150 outline-none select-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 active:not-aria-[haspopup]:translate-y-px disabled:pointer-events-none disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 motion-reduce:transition-none [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg]:transition-transform [&_svg]:duration-200 [&_svg]:ease-out motion-reduce:[&_svg]:transition-none [&_svg:not([class*='size-'])]:size-4`,
  {
    variants: {
      variant: {
        default:
          "bg-primary text-primary-foreground shadow-[inset_0_1px_0_oklch(1_0_0/0.35),0_1px_2px_oklch(0_0_0/0.12)] hover:bg-[color-mix(in_oklch,var(--primary),white_6%)] active:shadow-[inset_0_1px_2px_oklch(0_0_0/0.18)]",
        outline:
          "bg-muted/70 text-foreground shadow-xs hover:bg-muted aria-expanded:bg-muted dark:bg-input/30 dark:hover:bg-input/50",
        secondary: "bg-secondary text-secondary-foreground hover:bg-[color-mix(in_oklch,var(--secondary),var(--foreground)_5%)]",
        ghost: "text-foreground hover:bg-muted aria-expanded:bg-muted dark:hover:bg-muted/50",
        destructive: "bg-destructive/10 text-destructive hover:bg-destructive/15 focus-visible:border-destructive/40 focus-visible:ring-destructive/20 dark:bg-destructive/20",
        "solid-destructive": "bg-destructive text-white hover:bg-destructive/90 focus-visible:border-destructive/40 focus-visible:ring-destructive/30",
        link: "rounded-md text-foreground underline underline-offset-4 hover:text-muted-foreground",
      },
      size: {
        default: "h-(--ctl-h) gap-1.5 px-3 text-[0.8125rem]",
        xs: "h-5.5 gap-1 px-2 text-xs [&_svg:not([class*='size-'])]:size-3",
        sm: "h-6.5 gap-1.5 px-2.5 text-xs [&_svg:not([class*='size-'])]:size-3.5",
        lg: "h-10 gap-2 px-4 text-sm",
        icon: "size-(--ctl-h) hover:[&_svg]:scale-110",
        "icon-xs": "size-5.5 pointer-coarse:size-11 hover:[&_svg]:scale-110 [&_svg:not([class*='size-'])]:size-3",
        "icon-sm": "size-6.5 pointer-coarse:size-11 hover:[&_svg]:scale-110",
        "icon-lg": "size-10 hover:[&_svg]:scale-110",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  }
)

interface ButtonProps extends ButtonPrimitive.Props, VariantProps<typeof buttonVariants> {
  /** Icon before the label; it eases up on hover. */
  icon?: ReactNode
  /** Icon after the label (arrows, external links); it nudges right on hover. */
  iconEnd?: ReactNode
  loading?: boolean
  /** Required for icon-only sizes: becomes aria-label and tooltip text. */
  label?: string
  /** @deprecated No effect since the pill buttons were reverted; kept so existing call sites compile. */
  slide?: boolean
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars -- `slide` is accepted and dropped so it never reaches the DOM
function Button({ className, variant = "default", size = "default", icon, iconEnd, loading, label, slide: _slide, children, disabled, ...props }: ButtonProps) {
  const isIconOnly = typeof size === "string" && size.startsWith("icon")
  const button = (
    <ButtonPrimitive
      data-slot="button"
      className={cn(buttonVariants({ variant, size }), className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      aria-label={isIconOnly ? label : undefined}
      nativeButton={props.render ? false : undefined}
      {...props}
    >
      {loading ? <Spinner /> : icon && <span aria-hidden className="inline-flex motion-safe:group-hover/button:-translate-y-px transition-transform duration-200 ease-out">{icon}</span>}
      {children}
      {iconEnd && <span aria-hidden className="inline-flex motion-safe:group-hover/button:translate-x-0.5 transition-transform duration-200 ease-out">{iconEnd}</span>}
    </ButtonPrimitive>
  )
  if (!isIconOnly || !label) return button
  return (
    <Tooltip>
      <TooltipTrigger render={button} />
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  )
}

export { Button, buttonVariants }
