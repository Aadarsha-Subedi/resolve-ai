import type { ReactNode } from "react"
import { Check, Trash, X } from "@/icons"
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog"

/** Confirmation for destructive or irreversible steps. Names the action and what it affects. */
export function ConfirmDialog({ open, onOpenChange, title, description, confirmLabel = "Confirm", confirmIcon, destructive, onConfirm }: {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description: ReactNode
  confirmLabel?: string
  /** Icon on the confirm button; defaults to a bin for destructive steps and a check otherwise. */
  confirmIcon?: ReactNode
  destructive?: boolean
  onConfirm: () => void
}) {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription>{description}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel icon={<X />}>Cancel</AlertDialogCancel>
          <AlertDialogAction variant={destructive ? "destructive" : "default"} icon={confirmIcon ?? (destructive ? <Trash /> : <Check />)} onClick={onConfirm}>{confirmLabel}</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
