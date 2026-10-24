import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { TooltipProvider } from '@/components/ui/tooltip'
import { AiSettings } from '@/features/ai/ai-settings'
import type { LlmSettings } from '@/features/ai/api'
import { api } from '@/lib/api'

vi.mock('@/lib/api', async (original) => ({ ...(await original<typeof import('@/lib/api')>()), api: { get: vi.fn(), patch: vi.fn(), delete: vi.fn(), post: vi.fn(), put: vi.fn() } }))

const base: LlmSettings = {
  mode: 'resolve_ai',
  resolve_ai_model: 'gemini-3.5-flash-lite',
  active_provider: null,
  keys: [],
  usage: { used_today: 12, limit: 100, remaining: 88, resets_at: '2026-10-23T00:00:00Z' },
  options: {
    resolve_ai: { available: true, models: ['gemini-3.5-flash-lite', 'gemini-3.1-flash-lite'] },
    providers: { gemini: { models: ['gemini-3.5-flash-lite'], default: 'gemini-3.5-flash-lite' }, openai: { models: ['gpt-5-mini'], default: 'gpt-5-mini' } },
  },
}
const withGemini: LlmSettings = { ...base, mode: 'own_key', active_provider: 'gemini', keys: [{ provider: 'gemini', model: 'gemini-3.5-flash-lite', last4: 'wxyz', checked_at: '2026-10-22T10:00:00Z' }] }

function renderSettings(data: LlmSettings) {
  vi.mocked(api.get).mockResolvedValue({ data, meta: {}, message: '' })
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <TooltipProvider><AiSettings workspaceId="w1" /></TooltipProvider>
    </QueryClientProvider>,
  )
}

describe('AiSettings', () => {
  beforeEach(() => vi.clearAllMocks())

  it('shows today\'s usage and keeps the own-key option off until a key exists', async () => {
    renderSettings(base)
    expect(await screen.findByText(/12 of 100 searches used today/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'My API key' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Configure' })).toBeInTheDocument()
  })

  it('adds a key from the Configure dialog and sends it once', async () => {
    renderSettings(base)
    vi.mocked(api.put).mockResolvedValue({ data: withGemini, meta: {}, message: '' })
    await userEvent.click(await screen.findByRole('button', { name: 'Configure' }))
    await userEvent.click(await screen.findByRole('button', { name: 'Add key' }))
    await userEvent.type(await screen.findByLabelText('API key'), 'secret-key-wxyz')
    await userEvent.click(screen.getByRole('button', { name: 'Save key' }))
    expect(api.put).toHaveBeenCalledWith('/workspaces/w1/llm/keys/gemini/', { api_key: 'secret-key-wxyz' })
    expect(await screen.findByText(/ending in wxyz/)).toBeInTheDocument()
  })

  it('deletes a key after confirming', async () => {
    renderSettings(withGemini)
    vi.mocked(api.delete).mockResolvedValue({ data: base, meta: {}, message: '' })
    await userEvent.click(await screen.findByRole('button', { name: 'Configure' }))
    const dialog = await screen.findByRole('dialog')
    await userEvent.click(within(dialog).getByRole('button', { name: /Actions for the Google Gemini key/ }))
    await userEvent.click(await screen.findByRole('menuitem', { name: 'Delete' }))
    await userEvent.click(await screen.findByRole('button', { name: 'Delete key' }))
    expect(api.delete).toHaveBeenCalledWith('/workspaces/w1/llm/keys/gemini/')
  })
})
