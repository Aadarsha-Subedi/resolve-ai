import { Toaster as Sonner, type ToasterProps } from "sonner"
import { CheckCircle, CircleNotch, Info, Warning, XCircle } from "@/icons"
import { useTheme } from "@/hooks/use-theme"

/** Same icon language as inline banners: fill icon in the state color, neutral surface. */
const Toaster = ({ ...props }: ToasterProps) => {
  const { resolved } = useTheme()

  return (
    <Sonner
      theme={resolved}
      className="toaster group"
      icons={{
        success: <CheckCircle weight="fill" className="size-4 text-success" />,
        info: <Info weight="fill" className="size-4 text-info" />,
        warning: <Warning weight="fill" className="size-4 text-warning" />,
        error: <XCircle weight="fill" className="size-4 text-destructive" />,
        loading: <CircleNotch className="size-4 animate-spin text-muted-foreground" />,
      }}
      style={
        {
          "--normal-bg": "var(--popover)",
          "--normal-text": "var(--popover-foreground)",
          "--normal-border": "var(--border)",
          "--border-radius": "var(--radius)",
        } as React.CSSProperties
      }
      toastOptions={{
        classNames: {
          toast: "cn-toast !shadow-pop !font-sans !text-sm",
          title: "!font-medium",
          description: "!text-muted-foreground",
          actionButton: "!bg-transparent !text-primary !font-medium !underline-offset-2 hover:!underline",
          cancelButton: "!bg-muted !text-foreground",
        },
      }}
      {...props}
    />
  )
}

export { Toaster }
