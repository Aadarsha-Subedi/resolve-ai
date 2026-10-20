/** Two-letter initials from a name; falls back to "?". */
export function initials(name: string | undefined | null): string {
  const parts = (name ?? "").trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return "?"
  return (parts[0][0] + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase()
}

/** Plain dates ("2026-10-10") carry no time zone: format them without shifting the day. */
export function formatPlainDate(value: string | null | undefined): string {
  if (!value) return ""
  const [y, m, d] = value.split("-").map(Number)
  return new Date(y, m - 1, d).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" })
}

export function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" })
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit" })
}

/** "about 12 minutes", from a Retry-After in seconds. */
export function waitText(seconds: number): string {
  if (seconds <= 60) return seconds < 45 ? "under a minute" : "1 minute"
  const minutes = Math.ceil(seconds / 60)
  if (minutes < 60) return minutes === 1 ? "1 minute" : `about ${minutes} minutes`
  const hours = Math.ceil(minutes / 60)
  return hours === 1 ? "1 hour" : `about ${hours} hours`
}

/** Whole days from now until an ISO timestamp, never below 0. */
export function daysUntil(iso: string, now: number = Date.now()): number {
  return Math.max(0, Math.ceil((new Date(iso).getTime() - now) / 86_400_000))
}

export function plural(n: number, one: string, many = `${one}s`): string {
  return `${n} ${n === 1 ? one : many}`
}

/** Suggests a 2 to 5 letter task key from a project name: initials of words, else the first letters. */
export function suggestTaskKey(name: string): string {
  const words = name.toUpperCase().replace(/[^A-Z\s]/g, " ").split(/\s+/).filter(Boolean)
  if (words.length === 0) return ""
  const key = words.length > 1 ? words.map((w) => w[0]).join("") : words[0]
  return key.slice(0, 5)
}
