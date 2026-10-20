import { Button as ButtonPrimitive } from "@base-ui/react/button"
import type { ReactNode } from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"
import { Spinner } from "@/components/ui/spinner"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"

/**
 * Pill buttons. With an icon, the icon sits in a round chip at the trailing edge; on hover or focus the chip
 * glides to the leading edge while the label slides across (padding swap plus the chip's `right`, 500ms ease).
 * Reduced motion and touch skip the glide. `--chip` is the chip diameter, set per size.
 */
const EASE = "ease-[cubic-bezier(0.65,0,0.35,1)]"

const buttonVariants = cva(
  `group/button relative inline-flex shrink-0 pointer-coarse:min-h-11 cursor-pointer items-center justify-center rounded-full border border-transparent bg-clip-padding text-sm font-medium whitespace-nowrap transition-[background-color,box-shadow,border-color,padding-left,padding-right] duration-500 ${EASE} outline-none select-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 active:not-aria-[haspopup]:translate-y-px disabled:pointer-events-none disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 motion-reduce:transition-none [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4`,
  {
    variants: {
      variant: {
        default:
          "border-[color-mix(in_oklch,var(--primary),black_14%)] bg-primary text-primary-foreground shadow-[inset_0_1px_0_oklch(1_0_0/0.35),0_1px_2px_oklch(0_0_0/0.12)] hover:bg-[color-mix(in_oklch,var(--primary),white_6%)] active:shadow-[inset_0_1px_2px_oklch(0_0_0/0.18)]",
        outline:
          "border-border bg-background text-foreground shadow-xs hover:border-[color-mix(in_oklch,var(--border),var(--foreground)_18%)] hover:bg-muted aria-expanded:bg-muted dark:border-input dark:bg-input/30 dark:hover:bg-input/50",
        secondary: "bg-secondary text-secondary-foreground hover:bg-[color-mix(in_oklch,var(--secondary),var(--foreground)_5%)]",
        ghost: "text-foreground hover:bg-muted aria-expanded:bg-muted dark:hover:bg-muted/50",
        destructive: "bg-destructive/10 text-destructive hover:bg-destructive/15 focus-visible:border-destructive/40 focus-visible:ring-destructive/20 dark:bg-destructive/20",
        "solid-destructive": "bg-destructive text-white hover:bg-destructive/90 focus-visible:border-destructive/40 focus-visible:ring-destructive/30",
        link: "rounded-md text-foreground underline underline-offset-4 hover:text-muted-foreground",
      },
      size: {
        default: "h-(--ctl-h) gap-2 px-4 [--chip:calc(var(--ctl-h)-0.5rem)]",
        xs: "h-6 gap-1 px-2.5 text-xs [&_svg:not([class*='size-'])]:size-3",
        sm: "h-8 gap-1.5 px-3.5 text-xs [--chip:1.5rem] [&_svg:not([class*='size-'])]:size-3.5",
        lg: "h-11 gap-2 px-5 text-[0.9375rem] [--chip:calc(2.75rem-0.5rem)]",
        icon: "size-(--ctl-h)",
        "icon-xs": "size-6 pointer-coarse:size-11 [&_svg:not([class*='size-'])]:size-3",
        "icon-sm": "size-8 pointer-coarse:size-11",
        "icon-lg": "size-11",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  }
)

/** The chip has no background of its own: the icon is just the label's colour, so button, label and icon read as one surface. */

const SLIDE =
  "pl-3.5 pr-[calc(var(--chip)+0.375rem)] [@media(hover:hover)]:hover:pl-[calc(var(--chip)+0.375rem)] [@media(hover:hover)]:hover:pr-3.5 focus-visible:pl-[calc(var(--chip)+0.375rem)] focus-visible:pr-3.5"

interface ButtonProps extends ButtonPrimitive.Props, VariantProps<typeof buttonVariants> {
  /** Icon shown in the sliding chip. Link buttons and the xs size show it inline. */
  icon?: ReactNode
  /** Used as the chip icon when `icon` is absent (arrows, external links). */
  iconEnd?: ReactNode
  loading?: boolean
  /** Required for icon-only sizes: becomes aria-label and tooltip text. */
  label?: string
  /** Turn off the chip and slide, for buttons inside a button group or dense toolbars. */
  slide?: boolean
}

function Button({ className, variant = "default", size = "default", icon, iconEnd, loading, label, slide = true, children, disabled, ...props }: ButtonProps) {
  const isIconOnly = typeof size === "string" && size.startsWith("icon")
  const glyph = icon ?? iconEnd
  const chipped = slide && !isIconOnly && variant !== "link" && size !== "xs" && (glyph || loading)
  const button = (
    <ButtonPrimitive
      data-slot="button"
      className={cn(buttonVariants({ variant, size }), chipped && SLIDE, className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      aria-label={isIconOnly ? label : undefined}
      nativeButton={props.render ? false : undefined}
      {...props}
    >
      {chipped ? (
        <>
          <span className="relative z-10">{children}</span>
          <span
            aria-hidden
            data-slot="button-chip"
            className={cn(
              `absolute right-1 top-1/2 flex size-(--chip) -translate-y-1/2 items-center justify-center rounded-full transition-[right] duration-500 ${EASE} motion-reduce:transition-none`,
              "[@media(hover:hover)]:group-hover/button:right-[calc(100%-var(--chip)-0.25rem)] group-focus-visible/button:right-[calc(100%-var(--chip)-0.25rem)]",
            )}
          >
            {loading ? <Spinner /> : glyph}
          </span>
        </>
      ) : (
        <>
          {loading ? <Spinner /> : icon}
          {children}
          {iconEnd}
        </>
      )}
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
