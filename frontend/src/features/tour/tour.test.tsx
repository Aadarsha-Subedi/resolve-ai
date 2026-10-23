import { describe, expect, it } from 'vitest'

import { TOUR_STEPS, tourPageFor } from '@/features/tour/steps'

describe('tourPageFor', () => {
  it('maps workspace pages to their tour', () => {
    expect(tourPageFor('/app/w1')).toBe('dashboard')
    expect(tourPageFor('/app/w1/tickets')).toBe('tickets')
    expect(tourPageFor('/app/w1/tickets/t9')).toBe('ticket')
    expect(tourPageFor('/app/w1/knowledge')).toBe('knowledge')
    expect(tourPageFor('/app/w1/ask')).toBe('ask')
  })

  it('has no tour for account pages', () => {
    expect(tourPageFor('/app/account')).toBeNull()
    expect(tourPageFor('/app/new')).toBeNull()
  })

  it('gives every tour at least one step', () => {
    for (const steps of Object.values(TOUR_STEPS)) expect(steps.length).toBeGreaterThan(0)
  })
})
