import { formatDistanceToNowStrict } from 'date-fns'
import { useState, type FormEvent } from 'react'
import { toast } from 'sonner'

import { ConfirmDialog } from '@/components/patterns/confirm-dialog'
import { SoftBadge } from '@/components/patterns/ticket-meta'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { Field, FieldError } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { PROVIDER_LABELS, useRemoveLlmKey, useSaveLlmKey, useUpdateLlmSettings, type LlmKey, type LlmProvider, type LlmSettings } from '@/features/ai/api'
import { PROVIDER_LOGOS } from '@/features/ai/provider-logos'
import { Check, DotsThreeVertical, FloppyDisk, PencilSimple, Plus, Trash, X } from '@/icons'
import { errorMessage, fieldError } from '@/lib/api'

function ProviderName({ provider }: { provider: LlmProvider }) {
  const Logo = PROVIDER_LOGOS[provider]
  return <span className="flex items-center gap-2"><Logo className="size-4" />{PROVIDER_LABELS[provider]}</span>
}

/** Add a key (pick a provider, paste the key) or edit one (provider fixed; a new key and/or another model). */
function KeyFormDialog({ workspaceId, settings, editing, onClose }: { workspaceId: string; settings: LlmSettings; editing: LlmKey | null; onClose: () => void }) {
  const save = useSaveLlmKey(workspaceId)
  const free = (Object.keys(settings.options.providers) as LlmProvider[]).filter((p) => !settings.keys.some((k) => k.provider === p))
  const [provider, setProvider] = useState<LlmProvider>(editing?.provider ?? free[0])
  const [model, setModel] = useState(editing?.model ?? '')
  const [apiKey, setApiKey] = useState('')
  const models = settings.options.providers[provider].models
  const keyError = fieldError(save.error, 'api_key')
  const canSave = editing ? apiKey.trim().length >= 8 || (!!model && model !== editing.model) : apiKey.trim().length >= 8

  const submit = (event: FormEvent) => {
    event.preventDefault()
    save.mutate(
      { provider, ...(apiKey.trim() ? { api_key: apiKey.trim() } : {}), ...(editing && model && model !== editing.model ? { model } : {}) },
      { onSuccess: () => { toast.success(editing ? 'Key updated.' : 'Key saved.'); onClose() }, onError: (e) => !fieldError(e, 'api_key') && toast.error(errorMessage(e)) },
    )
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={submit} className="space-y-4">
          <DialogHeader>
            <DialogTitle>{editing ? `Edit ${PROVIDER_LABELS[editing.provider]} key` : 'Add API key'}</DialogTitle>
            <DialogDescription>The key is checked with the provider, stored encrypted and never shown again.</DialogDescription>
          </DialogHeader>
          <Field>
            <label htmlFor="key-provider" className="text-sm font-medium">Provider</label>
            <Select value={provider} disabled={!!editing} onValueChange={(v) => v != null && setProvider(v as LlmProvider)}>
              <SelectTrigger id="key-provider" className="w-full"><SelectValue>{(v: string | null) => (v ? <ProviderName provider={v as LlmProvider} /> : '')}</SelectValue></SelectTrigger>
              <SelectContent>{(editing ? [editing.provider] : free).map((p) => <SelectItem key={p} value={p}><ProviderName provider={p} /></SelectItem>)}</SelectContent>
            </Select>
          </Field>
          {editing && (
            <Field>
              <label htmlFor="key-model" className="text-sm font-medium">Model</label>
              <Select value={model} onValueChange={(v) => v != null && setModel(v)}>
                <SelectTrigger id="key-model" className="w-full"><SelectValue /></SelectTrigger>
                <SelectContent>{models.map((m) => <SelectItem key={m} value={m}>{m}</SelectItem>)}</SelectContent>
              </Select>
            </Field>
          )}
          <Field>
            <label htmlFor="key-value" className="text-sm font-medium">API key</label>
            <Input id="key-value" type="password" autoComplete="off" spellCheck={false} maxLength={512} value={apiKey} onChange={(e) => setApiKey(e.target.value)} aria-invalid={!!keyError}
              placeholder={editing ? `Ending in ${editing.last4}. Leave blank to keep it` : 'Paste your API key'} />
            <FieldError>{keyError}</FieldError>
          </Field>
          <DialogFooter>
            <Button type="button" variant="outline" icon={<X />} onClick={onClose}>Cancel</Button>
            <Button type="submit" icon={<FloppyDisk />} loading={save.isPending} disabled={!canSave}>{editing ? 'Save changes' : 'Save key'}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

/** The user's saved keys, one per provider: which one is in use, and Edit / Delete for each. */
export function AiKeysDialog({ workspaceId, settings, open, onOpenChange }: { workspaceId: string; settings: LlmSettings; open: boolean; onOpenChange: (open: boolean) => void }) {
  const update = useUpdateLlmSettings(workspaceId)
  const remove = useRemoveLlmKey(workspaceId)
  const [form, setForm] = useState<{ editing: LlmKey | null } | null>(null)
  const [deleting, setDeleting] = useState<LlmKey | null>(null)
  const canAdd = settings.keys.length < Object.keys(settings.options.providers).length

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Your API keys</DialogTitle>
            <DialogDescription>One key per provider. Only you can use them, and only in this workspace.</DialogDescription>
          </DialogHeader>
          {settings.keys.length === 0 ? <p className="py-6 text-center text-sm text-muted-foreground">No keys yet. Add one to use your own provider account.</p> : (
            <ul className="divide-y rounded-lg border" aria-label="API keys">
              {settings.keys.map((k) => {
                const inUse = settings.mode === 'own_key' && settings.active_provider === k.provider
                return (
                  <li key={k.provider} className="flex items-center gap-3 px-3 py-2.5">
                    <div className="min-w-0 flex-1 space-y-0.5">
                      <p className="flex flex-wrap items-center gap-2 text-sm font-medium"><ProviderName provider={k.provider} />{inUse && <SoftBadge tone="success" icon={Check}>In use</SoftBadge>}</p>
                      <p className="text-xs text-muted-foreground">{k.model} · ending in {k.last4} · checked {formatDistanceToNowStrict(new Date(k.checked_at), { addSuffix: true })}</p>
                    </div>
                    <DropdownMenu>
                      <DropdownMenuTrigger render={<Button variant="ghost" size="icon-sm" label={`Actions for the ${PROVIDER_LABELS[k.provider]} key`} />}><DotsThreeVertical weight="bold" /></DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="w-max min-w-40">
                        {!inUse && <DropdownMenuItem onClick={() => update.mutate({ mode: 'own_key', active_provider: k.provider }, { onSuccess: () => toast.success(`Now using ${PROVIDER_LABELS[k.provider]}.`), onError: (e) => toast.error(errorMessage(e)) })}><Check />Use this key</DropdownMenuItem>}
                        <DropdownMenuItem onClick={() => setForm({ editing: k })}><PencilSimple />Edit</DropdownMenuItem>
                        <DropdownMenuItem onClick={() => setDeleting(k)}><Trash />Delete</DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </li>
                )
              })}
            </ul>
          )}
          <DialogFooter>
            <Button type="button" variant="outline" icon={<X />} onClick={() => onOpenChange(false)}>Close</Button>
            <Button type="button" icon={<Plus />} disabled={!canAdd} onClick={() => setForm({ editing: null })}>Add key</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      {form && <KeyFormDialog workspaceId={workspaceId} settings={settings} editing={form.editing} onClose={() => setForm(null)} />}
      <ConfirmDialog
        open={!!deleting}
        onOpenChange={(o) => !o && setDeleting(null)}
        title={deleting ? `Delete the ${PROVIDER_LABELS[deleting.provider]} key?` : 'Delete key?'}
        description="It is removed for good. Searches use another saved key, or Resolve AI when there is none."
        confirmLabel="Delete key"
        destructive
        onConfirm={() => deleting && remove.mutate(deleting.provider, { onSuccess: () => toast.success('Key deleted.'), onError: (e) => toast.error(errorMessage(e)) })}
      />
    </>
  )
}
