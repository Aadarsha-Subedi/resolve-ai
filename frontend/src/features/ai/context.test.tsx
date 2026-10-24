import { render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { ContextResults } from '@/features/ai/context-panel'
import { splitCitations, splitHighlights, type ContextResult } from '@/features/ai/context-api'

vi.mock('@tanstack/react-router', () => ({ Link: ({ children, to, ...rest }: { children: ReactNode; to: string }) => <a href={to} {...rest}>{children}</a> }))

describe('splitHighlights', () => {
  it('turns markers into highlighted parts', () => {
    expect(splitHighlights('Reset your ⟦password⟧ from the ⟦login⟧ page')).toEqual([
      { text: 'Reset your ', hit: false }, { text: 'password', hit: true }, { text: ' from the ', hit: false }, { text: 'login', hit: true }, { text: ' page', hit: false },
    ])
  })
  it('never emits HTML and drops a stray marker', () => {
    expect(splitHighlights('<b>x</b> ⟦a⟧ ⟦broken')).toEqual([{ text: '<b>x</b> ', hit: false }, { text: 'a', hit: true }, { text: ' broken', hit: false }])
  })
})

const result = (over: Partial<ContextResult> = {}): ContextResult => ({
  terms: ['password'], queries: ['I forgot my password'], rewritten: false,
  results: [{ citation: 1, score: 0.4, article: { id: 'a1', title: 'Reset a password' }, section: 'Account > Reset', chunk_id: 'c1', snippet: 'Click ⟦reset⟧ on the login page' }],
  ...over,
})

describe('ContextResults', () => {
  it('lists numbered citations that link to the article and says when rewriting was skipped', () => {
    render(<ContextResults workspaceId="w1" result={result()} />)
    expect(screen.getByRole('link', { name: 'Reset a password' })).toHaveAttribute('href', '/app/w1/knowledge/a1')
    expect(screen.getByLabelText('Source 1')).toBeInTheDocument()
    expect(screen.getByText('reset').tagName).toBe('MARK')
    expect(screen.getByText(/Searched with your exact words/)).toBeInTheDocument()
  })
  it('shows an empty state without results', () => {
    render(<ContextResults workspaceId="w1" result={result({ results: [] })} />)
    expect(screen.getByText('No matching articles or documents')).toBeInTheDocument()
  })
})

describe('ContextResults for uploaded files', () => {
  const upload = (page: number | null) => result({ results: [{ citation: 1, score: 0.7, article: null, source: { type: 'upload', id: 'u1', title: 'Warranty.pdf', page }, section: 'Warranty > Exclusions', chunk_id: 'c9', snippet: 'Water damage is not covered' }] })
  it('names the file and page instead of linking to an article', () => {
    render(<ContextResults workspaceId="w1" result={upload(2)} />)
    expect(screen.getByText('Warranty.pdf')).toBeInTheDocument()
    expect(screen.getByText('page 2')).toBeInTheDocument()
    expect(screen.queryByRole('link')).toBeNull()
  })
  it('leaves the page out when it is unknown', () => {
    render(<ContextResults workspaceId="w1" result={upload(null)} />)
    expect(screen.queryByText(/^page/)).toBeNull()
  })
  it('still reads chats saved before files were searched (only `article`)', () => {
    render(<ContextResults workspaceId="w1" result={result()} />)
    expect(screen.getByRole('link', { name: 'Reset a password' })).toBeInTheDocument()
  })
})

describe('splitCitations', () => {
  it('marks [n] markers that point at a passage and leaves others as text', () => {
    expect(splitCitations('Refunds take 14 days [1][2] or never [7].', 2)).toEqual([
      { text: 'Refunds take 14 days ' }, { text: '[1]', cite: 1 }, { text: '[2]', cite: 2 }, { text: ' or never [7].' },
    ])
  })
})
