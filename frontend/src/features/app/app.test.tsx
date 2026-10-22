import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it } from 'vitest'

import { Restricted } from '@/components/patterns/restricted'
import { ShortcutsDialog, useShortcutsHotkey } from '@/components/patterns/shortcuts-menu'
import { TooltipProvider } from '@/components/ui/tooltip'
import { Button } from '@/components/ui/button'
import { validateAuditSearch } from '@/features/audit/search'
import { validateDashboardSearch } from '@/features/dashboard/search'
import { validateKnowledgeSearch } from '@/features/knowledge/search'
import { validateTicketSearch } from '@/features/tickets/search'
import { describeEvent } from '@/features/tickets/ticket-events'
import { formatBytes } from '@/lib/format'
import { queryClient } from '@/lib/query-client'
import type { TicketEvent } from '@/lib/types'

describe('Restricted', () => {
  it('renders the action untouched when allowed', () => {
    render(<Restricted reason={null}><Button>Save</Button></Restricted>)
    expect(screen.getByRole('button', { name: 'Save' })).toBeEnabled()
  })

  it('disables the action and explains why on hover', async () => {
    render(<TooltipProvider><Restricted reason="Only the workspace owner can do this."><Button>Delete</Button></Restricted></TooltipProvider>)
    expect(screen.getByRole('button', { name: 'Delete' })).toBeDisabled()
    await userEvent.hover(screen.getByRole('button', { name: 'Delete' }).parentElement!)
    expect(await screen.findByText('Only the workspace owner can do this.')).toBeInTheDocument()
  })
})

function ShortcutsHarness() {
  const [open, setOpen] = useState(false)
  useShortcutsHotkey(() => setOpen(true))
  return <ShortcutsDialog open={open} onOpenChange={setOpen} />
}

describe('ShortcutsDialog', () => {
  it('opens with ? and lists alternatives in one row', async () => {
    render(<TooltipProvider><ShortcutsHarness /></TooltipProvider>)
    expect(screen.queryByText('Go to')).not.toBeInTheDocument()
    await userEvent.keyboard('?')
    expect(await screen.findByText('Go to')).toBeInTheDocument()
    expect(screen.getAllByText('Search and jump to a page')).toHaveLength(1)
    expect(screen.getByLabelText('Meta+K or Ctrl+K')).toBeInTheDocument()
  })
})

describe('query client', () => {
  it('never retries or refetches on its own', () => {
    const q = queryClient.getDefaultOptions().queries!
    expect(q.retry).toBe(false)
    expect(q.refetchOnWindowFocus).toBe(false)
    expect(q.refetchOnReconnect).toBe(false)
    expect(q.refetchInterval).toBe(false)
  })
})

describe('URL search validation', () => {
  it('drops unknown ticket filters and keeps valid ones', () => {
    expect(validateTicketSearch({ status: 'bogus', priority: 'urgent', q: ' hello ', page: '3', created_from: '2026-01-02', created_to: 'x', waiting_for_reply: 'true', ordering: '-number' })).toEqual({
      status: undefined, priority: 'urgent', category: undefined, created_from: '2026-01-02', created_to: undefined, q: 'hello', waiting_for_reply: true, ordering: '-number', page: 3,
    })
    expect(validateTicketSearch({ ordering: 'password' }).ordering).toBeUndefined()
  })
  it('validates the other pages', () => {
    expect(validateDashboardSearch({ period: '7d' }).period).toBe('7d')
    expect(validateDashboardSearch({ period: '14d' }).period).toBeUndefined()
    expect(validateKnowledgeSearch({ view: 'graph', category: 'nope' })).toMatchObject({ view: 'graph', category: undefined })
    expect(validateAuditSearch({ action_prefix: 'member.' }).action_prefix).toBe('member.')
    expect(validateAuditSearch({ action_prefix: 'x.' }).action_prefix).toBeUndefined()
  })
})

describe('helpers', () => {
  it('describes history without needing message text', () => {
    const event = { id: '1', event_type: 'status_changed', actor: null, old_value: 'open', new_value: 'in_progress', metadata: {}, created_at: '2026-01-01T00:00:00Z' } as TicketEvent
    expect(describeEvent(event)).toBe('Status changed from Open to In progress')
  })
  it('formats bytes', () => {
    expect(formatBytes(512)).toBe('512 B')
    expect(formatBytes(1536)).toBe('1.5 KB')
    expect(formatBytes(10 * 1024 * 1024)).toBe('10 MB')
  })
})
