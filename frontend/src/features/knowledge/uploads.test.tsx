import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { uploadContentType } from '@/features/knowledge/api'
import { IndexStatusBadge } from '@/features/knowledge/index-status-badge'
import { failureMessage } from '@/features/knowledge/upload-failures'

describe('uploadContentType', () => {
  it('maps the four accepted extensions, whatever the browser reports', () => {
    expect(uploadContentType('Guide.PDF')).toBe('application/pdf')
    expect(uploadContentType('notes.md')).toBe('text/markdown')
    expect(uploadContentType('notes.txt')).toBe('text/plain')
    expect(uploadContentType('plan.docx')).toBe('application/vnd.openxmlformats-officedocument.wordprocessingml.document')
  })
  it('refuses legacy Word and other types', () => {
    expect(uploadContentType('old.doc')).toBeUndefined()
    expect(uploadContentType('archive.zip')).toBeUndefined()
    expect(uploadContentType('noextension')).toBeUndefined()
  })
})

describe('IndexStatusBadge', () => {
  it.each([
    ['pending', 'Waiting to be read'],
    ['indexing', 'Reading'],
    ['indexed', 'Searchable'],
    ['failed', 'Could not be read'],
  ] as const)('shows %s as "%s"', (status, label) => {
    render(<IndexStatusBadge status={status} />)
    expect(screen.getByText(label)).toBeInTheDocument()
  })
})

describe('failureMessage', () => {
  it('explains known codes and falls back for unknown ones', () => {
    expect(failureMessage('document_corrupt')).toMatch(/damaged/)
    expect(failureMessage('index_failed')).toMatch(/went wrong/)
    expect(failureMessage(null)).toMatch(/went wrong/)
  })
})
