import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { TooltipProvider } from '@/components/ui/tooltip'
import type { UsageLog } from '@/features/ai/usage-api'
import { UsagePage } from '@/features/ai/usage-page'
import { validateUsageSearch } from '@/features/ai/usage-search'
import { WorkspaceContext } from '@/features/app/workspace-context'
import { api } from '@/lib/api'
import type { Workspace } from '@/lib/types'

vi.mock('@tanstack/react-router', async (original) => ({ ...(await original<typeof import('@tanstack/react-router')>()), useNavigate: () => vi.fn() }))
vi.mock('@/lib/api', async (original) => ({ ...(await original<typeof import('@/lib/api')>()), api: { get: vi.fn(), patch: vi.fn(), delete: vi.fn(), post: vi.fn(), put: vi.fn() } }))

const hit: UsageLog = {
  id: 'u1',
  feature: 'ask',
  outcome: 'cache_hit',
  user: { id: 'm1', name: 'Dana' },
  provider: 'gemini',
  model: 'gemini-3.5-flash-lite',
  question: 'How long do refunds take?',
  answer: 'Refunds take 14 days. [1]',
  details: { similarity: 0.953, cached_question: 'How long for a refund?', passages: [{ citation: 1, title: 'Refund policy', section: 'Refunds', page: null, cited: true }] },
  input_tokens: 0,
  output_tokens: 0,
  error_code: '',
  created_at: '2026-10-28T13:00:00Z',
}
const call: UsageLog = { ...hit, id: 'u2', outcome: 'llm_call', question: 'Do you ship abroad?', answer: 'Yes.', details: {}, input_tokens: 120, output_tokens: 30 }

function renderPage(isOwner: boolean, items: UsageLog[] = [hit, call]) {
  vi.mocked(api.get).mockResolvedValue({
    data: { items },
    meta: { count: items.length, limit: 25, offset: 0, next: null, previous: null, summary: { total: 2, cache_hits: 1, llm_calls: 1, errors: 0, hit_rate: 0.5 } },
    message: '',
  })
  const workspace = { id: 'w1', name: 'Acme' } as Workspace
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <TooltipProvider>
        <WorkspaceContext.Provider value={{ workspace, role: isOwner ? 'owner' : 'member', isOwner }}>
          <UsagePage search={{}} />
        </WorkspaceContext.Provider>
      </TooltipProvider>
    </QueryClientProvider>,
  )
}

describe('UsagePage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('lists calls with the cache hit rate and opens the full question and answer', async () => {
    renderPage(true)
    expect(await screen.findByText(/1 of 2 answered calls came from the cache \(50%\)/)).toBeInTheDocument()
    expect(api.get).toHaveBeenCalledWith('/workspaces/w1/ai/usage/', expect.objectContaining({ limit: 25, offset: 0 }), expect.anything())
    expect(screen.getByText('From cache')).toBeInTheDocument()
    expect(screen.getByText('Sent to AI')).toBeInTheDocument()
    await userEvent.click(screen.getByText('How long do refunds take?'))
    const dialog = await screen.findByRole('dialog')
    expect(within(dialog).getByText('Refunds take 14 days. [1]')).toBeInTheDocument()
    expect(within(dialog).getByText('How long for a refund?')).toBeInTheDocument()
    expect(within(dialog).getByText(/95.3% similarity/)).toBeInTheDocument()
    expect(within(dialog).getByText('Cited')).toBeInTheDocument()
  })

  it('shows members nothing and never asks the server', () => {
    renderPage(false)
    expect(screen.getByText('Only the owner can read the AI usage log')).toBeInTheDocument()
    expect(api.get).not.toHaveBeenCalledWith('/workspaces/w1/ai/usage/', expect.anything(), expect.anything())
  })
})

describe('validateUsageSearch', () => {
  it('keeps valid values and drops the rest', () => {
    expect(validateUsageSearch({ q: ' refund ', feature: 'ask', outcome: 'bogus', ordering: '-tokens', page: '3', created_from: 'x' })).toEqual({
      q: 'refund',
      feature: 'ask',
      outcome: undefined,
      actor: undefined,
      created_from: undefined,
      created_to: undefined,
      ordering: '-tokens',
      page: 3,
    })
  })
})
