import { useEffect, useRef, useState } from "react"
import { Input } from "@/components/ui/input"
import { MagnifyingGlass } from "@/icons"

/** Typing waits 400 ms so each keystroke is not a request. The URL's value only overwrites the text when it changed elsewhere. */
export function SearchBox({ value, onCommit, placeholder }: { value: string; onCommit: (q: string | undefined) => void; placeholder: string }) {
  const [q, setQ] = useState(value)
  const [seen, setSeen] = useState(value)
  if (value !== seen) {
    setSeen(value)
    if (value !== q.trim()) setQ(value)
  }
  const commit = useRef(onCommit)
  useEffect(() => { commit.current = onCommit })
  useEffect(() => {
    if (q.trim() === value) return
    const t = setTimeout(() => commit.current(q.trim() || undefined), 400)
    return () => clearTimeout(t)
  }, [q, value])
  return (
    <div className="relative">
      <MagnifyingGlass className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
      <Input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={placeholder} aria-label={placeholder} className="w-72 max-w-full pl-8" />
    </div>
  )
}

