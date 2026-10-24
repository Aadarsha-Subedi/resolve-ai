/**
 * Typed fetch client for the Django backend. Session-cookie auth: requests send
 * cookies, and unsafe methods echo the `csrftoken` cookie in `X-CSRFToken`.
 * Every response uses the backend envelope; this unwraps it or throws ApiError.
 */

export type ApiMeta = Record<string, unknown>

export type ApiFieldError = { field?: string; message: string; code?: string }

type SuccessEnvelope<T> = {
  success: true
  status_code: number
  message: string
  data: T
  meta: ApiMeta
}

type ErrorEnvelope = {
  success: false
  status_code: number
  message: string
  code: string
  errors: ApiFieldError[]
}

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly errors: ApiFieldError[]

  constructor(
    status: number,
    message: string,
    code = 'unknown_error',
    errors: ApiFieldError[] = [],
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.errors = errors
  }
}

export type ApiResult<T> = { data: T; meta: ApiMeta; message: string }

const API_BASE = '/api'
const UNSAFE_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])

function readCookie(name: string): string | undefined {
  return document.cookie
    .split('; ')
    .find((row) => row.startsWith(`${name}=`))
    ?.slice(name.length + 1)
}

export type RequestOptions = {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  query?: Record<string, string | number | boolean | undefined | null>
  body?: unknown
  signal?: AbortSignal
}

function buildUrl(path: string, query?: RequestOptions['query']) {
  const url = new URL(`${API_BASE}${path}`, window.location.origin)
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null && value !== '')
      url.searchParams.set(key, String(value))
  }
  return url.pathname + url.search
}

let csrfSeeded: Promise<unknown> | null = null

/** The first write of a page load makes sure the csrftoken cookie exists (one GET, only when it is missing). */
async function ensureCsrf() {
  if (readCookie('csrftoken')) return
  csrfSeeded ??= fetch(`${API_BASE}/csrf/`, { credentials: 'include' }).catch(() => null)
  await csrfSeeded
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<ApiResult<T>> {
  const method = options.method ?? 'GET'
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (options.body !== undefined) headers['Content-Type'] = 'application/json'
  if (UNSAFE_METHODS.has(method)) {
    await ensureCsrf()
    const token = readCookie('csrftoken')
    if (token) headers['X-CSRFToken'] = decodeURIComponent(token)
  }

  let response: Response
  try {
    response = await fetch(buildUrl(path, options.query), {
      method,
      headers,
      credentials: 'include',
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: options.signal,
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ApiError(0, 'Could not reach the server. Check your connection.', 'network_error')
  }

  const payload = (await response.json().catch(() => null)) as
    SuccessEnvelope<T> | ErrorEnvelope | null

  if (!response.ok || !payload || payload.success !== true) {
    const failure = payload && payload.success === false ? payload : null
    throw new ApiError(
      response.status,
      failure?.message || response.statusText || 'Request failed',
      failure?.code,
      failure?.errors,
    )
  }
  return { data: payload.data, meta: payload.meta ?? {}, message: payload.message }
}

export const api = {
  get: <T>(path: string, query?: RequestOptions['query'], signal?: AbortSignal) =>
    apiRequest<T>(path, { query, signal }),
  post: <T>(path: string, body?: unknown) => apiRequest<T>(path, { method: 'POST', body }),
  put: <T>(path: string, body?: unknown) => apiRequest<T>(path, { method: 'PUT', body }),
  patch: <T>(path: string, body?: unknown) => apiRequest<T>(path, { method: 'PATCH', body }),
  delete: <T>(path: string) => apiRequest<T>(path, { method: 'DELETE' }),
}

/** A paginated list as the backend returns it: `data.items` plus `meta` (count, limit, offset). */
export type ListMeta = { count: number; limit: number; offset: number; next: string | null; previous: string | null }
export type Page<T> = { items: T[]; meta: ListMeta }

export async function apiList<T>(
  path: string,
  query?: RequestOptions['query'],
  signal?: AbortSignal,
): Promise<Page<T>> {
  const result = await api.get<{ items: T[] }>(path, query, signal)
  return { items: result.data.items, meta: result.meta as unknown as ListMeta }
}

/** Field-level message from a 400 response, if the backend named the field. */
export function fieldError(error: unknown, field: string): string | undefined {
  if (!(error instanceof ApiError)) return undefined
  return error.errors.find((e) => e.field === field)?.message
}

/** One-line message for toasts and inline errors. */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const first = error.errors[0]
    return first?.field ? `${first.field.replace(/_/g, ' ')}: ${first.message}` : error.message
  }
  return error instanceof Error ? error.message : 'Something went wrong.'
}
