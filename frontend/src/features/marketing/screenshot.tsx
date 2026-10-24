import { useState, type ReactNode } from "react"
import { cn } from "@/lib/utils"

/**
 * A real product screenshot from public/landing (see scripts/capture-screenshots.mjs), light and dark by the
 * visitor's theme. Until the files exist, or if one fails to load, the hand-built fragment stands in.
 */
export function Screenshot({ name, alt, fallback, className }: { name: string; alt: string; fallback: ReactNode; className?: string }) {
  const [failed, setFailed] = useState(false)
  if (failed) return <>{fallback}</>
  const frame = "overflow-hidden rounded-xl border bg-background shadow-[0_24px_48px_-24px_oklch(0_0_0/0.35)]"
  return (
    <div className={cn(frame, className)}>
      <img src={`/landing/${name}-light.png`} alt={alt} width={1280} height={800} loading="lazy" decoding="async" onError={() => setFailed(true)} className="block h-auto w-full dark:hidden" />
      <img src={`/landing/${name}-dark.png`} alt={alt} width={1280} height={800} loading="lazy" decoding="async" onError={() => setFailed(true)} className="hidden h-auto w-full dark:block" />
    </div>
  )
}
