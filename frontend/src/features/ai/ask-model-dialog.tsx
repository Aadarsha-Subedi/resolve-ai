import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { useLlmSettings } from '@/features/ai/api'
import { AskModelSelect } from '@/features/ai/ask-model-select'
import { ErrorPanel, LinesSkeleton } from '@/features/app/page-states'
import { X } from '@/icons'

/** Pick the model that answers: Resolve AI's, or the provider whose key is in use. Mounted only while open. */
export function AskModelDialog({ workspaceId, open, onOpenChange }: { workspaceId: string; open: boolean; onOpenChange: (open: boolean) => void }) {
  const settings = useLlmSettings(workspaceId)
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Model</DialogTitle>
          <DialogDescription>{settings.data?.mode === 'own_key' ? 'The model of the provider whose key you are using.' : 'The model Resolve AI uses to write answers.'}</DialogDescription>
        </DialogHeader>
        {settings.isPending ? <LinesSkeleton rows={1} />
          : settings.error ? <ErrorPanel error={settings.error} onRetry={() => void settings.refetch()} title="Models could not be loaded" />
          : <AskModelSelect workspaceId={workspaceId} settings={settings.data} />}
        <DialogFooter>
          <Button type="button" variant="outline" icon={<X />} onClick={() => onOpenChange(false)}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
