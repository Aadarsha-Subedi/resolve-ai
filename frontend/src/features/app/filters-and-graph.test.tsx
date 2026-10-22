import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it } from 'vitest'

import { compactRange, FilterBar } from '@/components/patterns/filter-bar'
import type { IsoRange } from '@/components/patterns/date-picker'
import { STATUS_OPTIONS } from '@/components/patterns/ticket-meta'
import { TooltipProvider } from '@/components/ui/tooltip'
import type { Article, Category, Upload } from '@/features/knowledge/api'
import { buildKnowledgeGraph, UNCATEGORIZED_ID } from '@/features/knowledge/graph-layout'
import { validateKnowledgeSearch } from '@/features/knowledge/search'
import { validateTicketSearch } from '@/features/tickets/search'
import { describeEvent } from '@/features/tickets/ticket-events'
import type { TicketEvent } from '@/lib/types'

function Harness({ initial = {} }: { initial?: { status?: string; waiting?: boolean; range?: IsoRange } }) {
  const [status, setStatus] = useState<string | undefined>(initial.status)
  const [waiting, setWaiting] = useState<boolean | undefined>(initial.waiting)
  const [range, setRange] = useState<IsoRange>(initial.range ?? {})
  const [q, setQ] = useState('')
  return (
    <TooltipProvider>
      <FilterBar
        search={{ value: q, onCommit: (v) => setQ(v ?? ''), placeholder: 'Search things' }}
        filters={[
          { id: 'status', kind: 'select', label: 'Status', options: STATUS_OPTIONS, value: status, onChange: setStatus },
          { id: 'created', kind: 'date-range', label: 'Created', value: range, onChange: setRange },
          { id: 'waiting', kind: 'boolean', label: 'Waiting for reply', value: waiting, onChange: setWaiting },
        ]}
        onClearAll={() => { setStatus(undefined); setWaiting(undefined); setRange({}); setQ('') }}
      />
    </TooltipProvider>
  )
}

describe('FilterBar', () => {
  it('shows only a Filter button and no Clear all when nothing is applied', () => {
    render(<Harness />)
    expect(screen.getByRole('button', { name: 'Add filter' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Clear all' })).not.toBeInTheDocument()
  })

  it('adds a boolean filter as a chip with no value, removes it, and offers it again', async () => {
    render(<Harness />)
    await userEvent.click(screen.getByRole('button', { name: 'Add filter' }))
    await userEvent.click(await screen.findByRole('menuitem', { name: 'Waiting for reply' }))
    expect(screen.getByRole('button', { name: 'Remove Waiting for reply filter' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Clear all' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Remove Waiting for reply filter' }))
    expect(screen.queryByRole('button', { name: 'Remove Waiting for reply filter' })).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Add filter' }))
    expect(await screen.findByRole('menuitem', { name: 'Waiting for reply' })).toBeInTheDocument()
  })

  it('adds a select filter by choosing its value and shows it as "Status: Open"', async () => {
    render(<Harness />)
    await userEvent.click(screen.getByRole('button', { name: 'Add filter' }))
    await userEvent.click(await screen.findByRole('menuitem', { name: 'Status' }))
    await userEvent.click(await screen.findByRole('menuitemradio', { name: 'Open' }))
    const chip = await screen.findByRole('button', { name: /Status: Open/ })
    expect(chip).toHaveTextContent('Status:')
    expect(chip).toHaveTextContent('Open')
    expect(screen.getByRole('button', { name: 'Remove Status filter' })).toBeInTheDocument()
  })

  it('shows an applied date range as a compact chip and clears everything', async () => {
    render(<Harness initial={{ status: 'open', range: { from: '2020-10-01', to: '2020-10-20' } }} />)
    const day = (d: number) => new Date(2020, 9, d).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
    expect(screen.getByRole('button', { name: new RegExp(`Created: ${day(1)} - ${day(20)}`) })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Clear all' }))
    expect(screen.queryByRole('button', { name: /Remove/ })).not.toBeInTheDocument()
  })

  it('removes one chip without touching the others', async () => {
    render(<Harness initial={{ status: 'open', waiting: true }} />)
    await userEvent.click(screen.getByRole('button', { name: 'Remove Status filter' }))
    expect(screen.queryByRole('button', { name: /Status/ })).not.toBeInTheDocument()
    expect(within(screen.getByRole('search')).getByRole('button', { name: 'Remove Waiting for reply filter' })).toBeInTheDocument()
  })

  it('leaves the year out only for the current year, in the browser locale', () => {
    const year = new Date().getFullYear()
    const short = (d: number) => new Date(year, 9, d).toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
    expect(compactRange({ from: `${year}-10-01`, to: `${year}-10-20` })).toBe(`${short(1)} - ${short(20)}`)
    expect(compactRange({ from: '2020-10-01', to: '2020-10-20' })).toContain('2020')
  })
})

describe('URL state keeps working', () => {
  it('accepts me, unassigned or a user id for the assignee and drops anything else', () => {
    expect(validateTicketSearch({ assignee: 'me' }).assignee).toBe('me')
    expect(validateTicketSearch({ assignee: 'unassigned' }).assignee).toBe('unassigned')
    expect(validateTicketSearch({ assignee: '0198a1b2-c3d4-7e5f-8a9b-0c1d2e3f4a5b' }).assignee).toBe('0198a1b2-c3d4-7e5f-8a9b-0c1d2e3f4a5b')
    expect(validateTicketSearch({ assignee: 'everyone' }).assignee).toBeUndefined()
  })

  it('keeps only a known graph view and no longer has a files tab', () => {
    expect(validateKnowledgeSearch({ view: 'graph' }).view).toBe('graph')
    expect(validateKnowledgeSearch({ tab: 'files' })).not.toHaveProperty('tab')
    expect(validateKnowledgeSearch({ view: 'x' }).view).toBeUndefined()
  })
})

describe('assignee history', () => {
  const event = (partial: Partial<TicketEvent>) => ({ id: '1', event_type: 'assignee_changed', actor: null, old_value: null, new_value: null, metadata: {}, created_at: '2026-10-21T00:00:00Z', ...partial }) as TicketEvent
  it('describes assigning, reassigning and unassigning', () => {
    expect(describeEvent(event({ new_value: { id: 'a', display_name: 'Ana' } }))).toBe('Assigned to Ana')
    expect(describeEvent(event({ old_value: { id: 'a', display_name: 'Ana' }, new_value: { id: 'b', display_name: 'Ben' } }))).toBe('Reassigned from Ana to Ben')
    expect(describeEvent(event({ old_value: { id: 'a', display_name: 'Ana' } }))).toBe('Unassigned from Ana')
  })
  it('explains an automatic unassignment', () => {
    expect(describeEvent(event({ old_value: { id: 'a', display_name: 'Ana' }, metadata: { reason: 'member_left' } }))).toContain('left the workspace')
  })
})

const cat = (id: string, name: string): Category => ({ id, name, slug: name.toLowerCase() })
const art = (id: string, title: string, categories: Category[]): Article => ({ id, title, status: 'published', categories, size_bytes: 1, created_by: null, updated_by: null, created_at: '', updated_at: '', published_at: null })

const file = (id: string, filename: string, category: Category | null): Upload => ({ id, category, filename, content_type: 'application/pdf', size_bytes: 10, status: 'ready', uploaded_by: null, created_at: '' })

describe('buildKnowledgeGraph', () => {
  const billing = cat('c1', 'Billing')
  const tech = cat('c2', 'Technical')
  it('connects each category to its articles, one edge per membership', () => {
    const { nodes, edges } = buildKnowledgeGraph([billing, tech], [art('a1', 'Refunds', [billing]), art('a2', 'Invoices and API', [billing, tech])])
    expect(nodes.filter((n) => n.type === 'category')).toHaveLength(2)
    expect(nodes.filter((n) => n.type === 'article')).toHaveLength(2)
    expect(edges.map((e) => e.id).sort()).toEqual(['e:c1:a1', 'e:c1:a2', 'e:c2:a2'])
    expect(edges.every((e) => e.source.startsWith('c:') && e.target.startsWith('a:'))).toBe(true)
  })
  it('hangs articles without a category off an Uncategorized node', () => {
    const { nodes, edges } = buildKnowledgeGraph([billing], [art('a1', 'Loose', [])])
    expect(nodes.some((n) => n.id === `c:${UNCATEGORIZED_ID}`)).toBe(true)
    expect(edges).toEqual([{ id: `e:${UNCATEGORIZED_ID}:a1`, source: `c:${UNCATEGORIZED_ID}`, target: 'a:a1' }])
  })
  it('never stacks two categories on the same spot', () => {
    const { nodes } = buildKnowledgeGraph([billing, tech], [art('a1', 'Shared', [billing, tech])])
    const ys = nodes.filter((n) => n.type === 'category').map((n) => n.position.y)
    expect(new Set(ys).size).toBe(ys.length)
  })
  it('hangs files off their category, next to the articles', () => {
    const { nodes, edges } = buildKnowledgeGraph([billing, tech], [art('a1', 'Refunds', [billing])], [file('f1', 'Tariffs.pdf', billing), file('f2', 'Loose.pdf', null)])
    expect(nodes.filter((n) => n.type === 'file').map((n) => n.id).sort()).toEqual(['f:f1', 'f:f2'])
    expect(edges.map((e) => `${e.source}>${e.target}`).sort()).toEqual([`c:${UNCATEGORIZED_ID}>f:f2`, 'c:c1>a:a1', 'c:c1>f:f1'])
    expect(nodes.some((n) => n.id === `c:${UNCATEGORIZED_ID}`)).toBe(true)
  })
  it('draws an empty category without edges', () => {
    const { nodes, edges } = buildKnowledgeGraph([billing], [])
    expect(nodes).toHaveLength(1)
    expect(edges).toHaveLength(0)
  })
})
