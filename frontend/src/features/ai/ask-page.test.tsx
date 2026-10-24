import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { TooltipProvider } from '@/components/ui/tooltip'
import type { LlmSettings } from '@/features/ai/api'
import { AskPage } from '@/features/ai/ask-page'
import type { AskTurn, Conversation, NewAskTurn } from '@/features/ai/context-api'
import { api } from '@/lib/api'

vi.mock('@tanstack/react-router', () => ({ useNavigate: () => vi.fn(), Link: ({ children, to, ...rest }: { children: ReactNode; to: string }) => <a href={to} {...rest}>{children}</a> }))
vi.mock('@/features/auth/api', () => ({ currentUserQuery: { queryKey: ['me'], queryFn: async () => ({ display_name: 'Ada Lovelace' }) } }))
vi.mock('@/features/app/workspace-context', () => ({ useWorkspace: () => ({ workspace: { id: 'w1', name: 'Acme' }, role: 'member', isOwner: false }) }))
vi.mock('@/lib/api', async (original) => ({ ...(await original<typeof import('@/lib/api')>()), api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn(), put: vi.fn() } }))

const settings = (over: Partial<LlmSettings['usage']> = {}, mode: LlmSettings['mode'] = 'resolve_ai'): LlmSettings => ({
  mode,
  resolve_ai_model: 'gemini-3.5-flash-lite',
  active_provider: null,
  keys: [],
  usage: { used_today: 12, limit: 100, remaining: 88, resets_at: '2026-10-23T00:00:00Z', ...over },
  options: { resolve_ai: { available: true, models: ['gemini-3.5-flash-lite', 'gemini-3.1-flash-lite'] }, providers: { gemini: { models: [], default: '' }, openai: { models: [], default: '' } } },
})

const turn = (over: Partial<AskTurn> = {}): AskTurn => ({
  turn_id: 't1', question: 'How do refunds work?', created_at: '2026-10-22T10:00:00Z',
  terms: ['refund'], queries: [], rewritten: false, status: 'answered', answer: 'Annual plans can be refunded within 14 days [1].', cited: [1],
  results: [{ citation: 1, score: 0.4, article: { id: 'a1', title: 'Refund policy' }, section: 'Annual plans', chunk_id: 'c1', snippet: 'a ⟦refund⟧ within 14 days' }],
  ...over,
})

const saved: Conversation = { id: 'c1', title: 'Earlier question', created_at: '2026-10-21T10:00:00Z', updated_at: '2026-10-21T10:00:00Z', turn_count: 1 }

function setup(llm: LlmSettings = settings(), conversations: Conversation[] = []) {
  vi.mocked(api.get).mockImplementation((async (path: string) => {
    if (path.endsWith('/llm/')) return { data: llm, meta: {}, message: '' }
    if (path.endsWith('/ask/conversations/')) return { data: { items: conversations }, meta: { count: conversations.length, limit: 50, offset: 0, next: null, previous: null }, message: '' }
    return { data: { ...saved, turns: [turn({ question: 'Earlier question' })] }, meta: {}, message: '' }
  }) as never)
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><TooltipProvider><AskPage /></TooltipProvider></QueryClientProvider>)
}

describe('AskPage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('shows the question and the agent answer as chat messages with linked sources', async () => {
    setup()
    const reply: NewAskTurn = { ...turn(), conversation_id: 'c9' }
    vi.mocked(api.post).mockResolvedValue({ data: reply, meta: {}, message: '' })
    await userEvent.type(screen.getByLabelText('Your question'), 'How do refunds work?')
    await userEvent.click(screen.getByRole('button', { name: 'Send question' }))
    expect(api.post).toHaveBeenCalledWith('/workspaces/w1/knowledge/ask/', { query: 'How do refunds work?' })
    expect(await screen.findByRole('link', { name: '[1]' })).toHaveAttribute('href', '#src-t1-1')
    expect(screen.getByText(/Sources \(1\)/).closest('details')).not.toHaveAttribute('open')
    expect(screen.getByText('Resolve AI')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Refund policy' })).toBeInTheDocument()
  })

  it('says Resolve AI uses a free model', async () => {
    setup()
    expect(await screen.findByText('Resolve AI uses a free model, responses may be slower')).toBeInTheDocument()
  })

  it('blocks asking when the daily limit is spent', async () => {
    setup(settings({ used_today: 100, remaining: 0 }))
    expect(await screen.findByText(/Daily limit reached/)).toBeInTheDocument()
    expect(screen.getByLabelText('Your question')).toBeDisabled()
  })

  it('shows usage and the reset time in a popup from the options menu', async () => {
    setup()
    await userEvent.click(screen.getByRole('button', { name: 'Chat options' }))
    await userEvent.click(await screen.findByRole('menuitem', { name: 'Usage' }))
    expect(await screen.findByText(/12 of 100/)).toBeInTheDocument()
    expect(screen.getByText(/Resets/)).toBeInTheDocument()
  })

  it('opens the history from the options menu and loads the chat that is picked', async () => {
    setup(settings(), [saved])
    await userEvent.click(screen.getByRole('button', { name: 'Chat options' }))
    await userEvent.click(await screen.findByRole('menuitem', { name: 'Chat history' }))
    await userEvent.click(await screen.findByRole('button', { name: /Earlier question/ }))
    await waitFor(() => expect(screen.getByRole('list', { name: 'Messages' })).toBeInTheDocument())
    expect(screen.getByRole('link', { name: 'Refund policy' })).toBeInTheDocument()
  })

  it('starts a new chat from the options menu', async () => {
    setup(settings(), [saved])
    await userEvent.click(screen.getByRole('button', { name: 'Chat options' }))
    await userEvent.click(await screen.findByRole('menuitem', { name: 'Chat history' }))
    await userEvent.click(await screen.findByRole('button', { name: /Earlier question/ }))
    await screen.findByRole('list', { name: 'Messages' })
    await userEvent.click(screen.getByRole('button', { name: 'Chat options' }))
    await userEvent.click(await screen.findByRole('menuitem', { name: 'New chat' }))
    expect(await screen.findByRole('heading', { name: /Ada$/ })).toBeInTheDocument()
  })

  it('says why no answer could be written when the provider has no credit', async () => {
    setup()
    vi.mocked(api.post).mockResolvedValue({ data: { ...turn({ status: 'unavailable', reason: 'llm_insufficient_quota', answer: null, cited: [] }), conversation_id: 'c9' }, meta: {}, message: '' })
    await userEvent.type(screen.getByLabelText('Your question'), 'How do refunds work?')
    await userEvent.click(screen.getByRole('button', { name: 'Send question' }))
    expect(await screen.findByText(/has no credit or quota left/)).toBeInTheDocument()
  })

  it('tells the user when nothing was found', async () => {
    setup()
    vi.mocked(api.post).mockResolvedValue({ data: { ...turn({ status: 'no_results', answer: null, cited: [], results: [] }), conversation_id: 'c9' }, meta: {}, message: '' })
    await userEvent.type(screen.getByLabelText('Your question'), 'zebra unicycle')
    await userEvent.click(screen.getByRole('button', { name: 'Send question' }))
    expect(await screen.findByText(/No matching articles/)).toBeInTheDocument()
  })
})

describe('AskPage model selector', () => {
  beforeEach(() => vi.clearAllMocks())

  it('changes the Resolve AI model', async () => {
    setup()
    vi.mocked(api.patch).mockResolvedValue({ data: settings(), meta: {}, message: '' })
    await userEvent.click(screen.getByRole('button', { name: 'Chat options' }))
    await userEvent.click(await screen.findByRole('menuitem', { name: 'Model' }))
    await userEvent.click(await screen.findByRole('combobox', { name: 'Model (Resolve AI)' }))
    await userEvent.click(await screen.findByRole('option', { name: 'gemini-3.1-flash-lite' }))
    expect(api.patch).toHaveBeenCalledWith('/workspaces/w1/llm/', { resolve_ai_model: 'gemini-3.1-flash-lite' })
  })

  it('changes the model of the provider in use when answering with an own key', async () => {
    const own: LlmSettings = {
      ...settings({}, 'own_key'), active_provider: 'openai',
      keys: [{ provider: 'openai', model: 'gpt-5-mini', last4: 'wxyz', checked_at: '2026-10-22T10:00:00Z' }],
      options: { resolve_ai: { available: true, models: [] }, providers: { gemini: { models: ['gemini-3.5-flash-lite'], default: 'gemini-3.5-flash-lite' }, openai: { models: ['gpt-5-mini', 'gpt-5-nano'], default: 'gpt-5-mini' } } },
    }
    setup(own)
    vi.mocked(api.put).mockResolvedValue({ data: own, meta: {}, message: '' })
    await userEvent.click(screen.getByRole('button', { name: 'Chat options' }))
    await userEvent.click(await screen.findByRole('menuitem', { name: 'Model' }))
    await userEvent.click(await screen.findByRole('combobox', { name: 'Model (OpenAI)' }))
    await userEvent.click(await screen.findByRole('option', { name: 'gpt-5-nano' }))
    expect(api.put).toHaveBeenCalledWith('/workspaces/w1/llm/keys/openai/', { model: 'gpt-5-nano' })
  })
})

describe('AskPage empty state', () => {
  it('greets a new chat by first name', async () => {
    setup()
    expect(await screen.findByRole('heading', { name: /, Ada$/ })).toBeInTheDocument()
  })
})
