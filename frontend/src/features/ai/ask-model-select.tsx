import { toast } from 'sonner'

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { PROVIDER_LABELS, useSaveLlmKey, useUpdateLlmSettings, type LlmSettings } from '@/features/ai/api'
import { PROVIDER_LOGOS } from '@/features/ai/provider-logos'
import { errorMessage } from '@/lib/api'

/** Picks the model that answers: Resolve AI's models, or the models of the provider whose key is in use. */
export function AskModelSelect({ workspaceId, settings }: { workspaceId: string; settings: LlmSettings }) {
  const updateSettings = useUpdateLlmSettings(workspaceId)
  const saveKey = useSaveLlmKey(workspaceId)
  const active = settings.mode === 'own_key' ? settings.keys.find((k) => k.provider === settings.active_provider) : undefined
  const ownKey = settings.mode === 'own_key' && active
  const models = ownKey ? settings.options.providers[active.provider].models : settings.options.resolve_ai.models
  const value = ownKey ? active.model : settings.resolve_ai_model
  const Logo = ownKey ? PROVIDER_LOGOS[active.provider] : null
  const pending = updateSettings.isPending || saveKey.isPending
  if (models.length === 0 && !value) return null

  const onError = (e: unknown) => toast.error(errorMessage(e))
  const pick = (model: string | null) => {
    if (!model || model === value) return
    if (ownKey) saveKey.mutate({ provider: active.provider, model }, { onError })
    else updateSettings.mutate({ resolve_ai_model: model }, { onError })
  }

  return (
    <Select value={value} disabled={pending} onValueChange={pick}>
      <SelectTrigger aria-label={ownKey ? `Model (${PROVIDER_LABELS[active.provider]})` : 'Model (Resolve AI)'} className="w-full">
        {Logo && <Logo className="size-4 shrink-0" />}
        <SelectValue />
      </SelectTrigger>
      <SelectContent>{(models.includes(value) ? models : [value, ...models]).map((m) => <SelectItem key={m} value={m}>{m}</SelectItem>)}</SelectContent>
    </Select>
  )
}
