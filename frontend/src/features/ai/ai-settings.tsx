import { useState } from 'react'
import { toast } from 'sonner'

import { SettingGroup, SettingRow } from '@/components/patterns/setting-row'
import { StatusBanner } from '@/components/patterns/status-banner'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { AiKeysDialog } from '@/features/ai/ai-keys-dialog'
import {
  PROVIDER_LABELS,
  useLlmSettings,
  useUpdateLlmSettings,
  type LlmMode,
  type LlmSettings,
} from '@/features/ai/api'
import { ErrorPanel, LinesSkeleton } from '@/features/app/page-states'
import { Gear } from '@/icons'
import { errorMessage } from '@/lib/api'

const MODES: { value: LlmMode; label: string }[] = [
  { value: 'resolve_ai', label: 'Resolve AI' },
  { value: 'own_key', label: 'My API key' },
]

function resetTime(iso: string) {
  return new Date(iso).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
}

/** "AI assistant" group of the settings page. Per user and per workspace: every member sees their own. */
export function AiSettings({ workspaceId }: { workspaceId: string }) {
  const settings = useLlmSettings(workspaceId)
  return (
    <SettingGroup id="ai" title="AI assistant">
      {settings.isPending ? (
        <div className="py-4">
          <LinesSkeleton />
        </div>
      ) : settings.error ? (
        <div className="py-4">
          <ErrorPanel error={settings.error} onRetry={() => void settings.refetch()} />
        </div>
      ) : (
        <AiSettingsRows workspaceId={workspaceId} settings={settings.data} />
      )}
    </SettingGroup>
  )
}

function AiSettingsRows({ workspaceId, settings }: { workspaceId: string; settings: LlmSettings }) {
  const update = useUpdateLlmSettings(workspaceId)
  const [configuring, setConfiguring] = useState(false)
  const { options, keys, usage } = settings
  const active = keys.find((k) => k.provider === settings.active_provider)

  const change = (body: Parameters<typeof update.mutate>[0], done?: string) =>
    update.mutate(body, {
      onSuccess: () => done && toast.success(done),
      onError: (e) => toast.error(errorMessage(e)),
    })

  return (
    <>
      <SettingRow
        title="Who answers"
        description="Used for finding articles that match a ticket or a question. Only you see and change this, and only in this workspace."
      >
        <div role="group" aria-label="Who answers" className="inline-flex rounded-lg border p-0.5">
          {MODES.map((m) => (
            <Button
              key={m.value}
              size="sm"
              variant={settings.mode === m.value ? 'secondary' : 'ghost'}
              aria-pressed={settings.mode === m.value}
              disabled={
                update.isPending ||
                (m.value === 'own_key' && keys.length === 0) ||
                (m.value === 'resolve_ai' && !options.resolve_ai.available)
              }
              onClick={() =>
                settings.mode !== m.value && change({ mode: m.value }, `Now using ${m.label}.`)
              }
            >
              {m.label}
            </Button>
          ))}
        </div>
      </SettingRow>

      {!options.resolve_ai.available && (
        <div className="py-3">
          <StatusBanner tone="warning" title="Resolve AI is not set up on this server.">
            Add your own key to use the assistant.
          </StatusBanner>
        </div>
      )}

      <SettingRow
        title="Resolve AI model"
        htmlFor="ai-resolve-model"
        description={`${usage.used_today} of ${usage.limit} searches used today. The count resets at ${resetTime(usage.resets_at)}. Searches with your own key are not counted.`}
      >
        <Select
          value={settings.resolve_ai_model}
          disabled={update.isPending || !options.resolve_ai.available}
          onValueChange={(v) => v != null && change({ resolve_ai_model: v }, 'Model updated.')}
        >
          <SelectTrigger id="ai-resolve-model" className="w-56 max-w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {options.resolve_ai.models.map((m) => (
              <SelectItem key={m} value={m}>
                {m}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </SettingRow>

      <SettingRow
        title="Your own API keys"
        description={
          keys.length === 0
            ? 'Use your own Gemini or OpenAI account. Keys are stored encrypted and never shown again. Your provider limits and bills these searches.'
            : `${keys.length} saved${active && settings.mode === 'own_key' ? `. In use: ${PROVIDER_LABELS[active.provider]}, ${active.model}.` : '.'}`
        }
      >
        <Button variant="outline" icon={<Gear />} onClick={() => setConfiguring(true)}>
          Configure
        </Button>
      </SettingRow>
      {configuring && (
        <AiKeysDialog
          workspaceId={workspaceId}
          settings={settings}
          open
          onOpenChange={setConfiguring}
        />
      )}
    </>
  )
}
