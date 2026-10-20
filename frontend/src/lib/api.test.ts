import { afterEach, describe, expect, it, vi } from 'vitest'

import { ApiError, api } from '@/lib/api'

function mockFetch(status: number, body: unknown) {
  const fn = vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status }))
  vi.stubGlobal('fetch', fn)
  return fn
}

afterEach(() => {
  vi.unstubAllGlobals()
  document.cookie = 'csrftoken=; max-age=0'
})

describe('api client', () => {
  it('unwraps the success envelope', async () => {
    mockFetch(200, {
      success: true,
      status_code: 200,
      message: 'ok',
      data: { a: 1 },
      meta: { count: 1 },
    })
    const result = await api.get<{ a: number }>('/tickets/', { q: 'x' })
    expect(result.data).toEqual({ a: 1 })
    expect(result.meta).toEqual({ count: 1 })
  })

  it('sends the CSRF header on writes', async () => {
    document.cookie = 'csrftoken=abc123'
    const fn = mockFetch(200, {
      success: true,
      status_code: 200,
      message: '',
      data: null,
      meta: {},
    })
    await api.post('/tickets/', { subject: 's' })
    const init = fn.mock.calls[0]![1] as RequestInit
    expect((init.headers as Record<string, string>)['X-CSRFToken']).toBe('abc123')
    expect(init.credentials).toBe('include')
  })

  it('throws ApiError with the backend code', async () => {
    mockFetch(403, {
      success: false,
      status_code: 403,
      message: 'Nope',
      code: 'permission_denied',
      errors: [],
    })
    await expect(api.get('/x/')).rejects.toMatchObject({ status: 403, code: 'permission_denied' })
    await expect(api.get('/x/')).rejects.toBeInstanceOf(ApiError)
  })
})
