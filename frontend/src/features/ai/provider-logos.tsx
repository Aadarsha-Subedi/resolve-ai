import type { ComponentType, SVGProps } from 'react'

import type { LlmProvider } from '@/features/ai/api'

type LogoProps = SVGProps<SVGSVGElement>

/** Simple marks drawn for this app (a four-point spark and a six-petal knot), not the providers' official artwork. */
export function GeminiLogo(props: LogoProps) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden {...props}>
      <path d="M12 1.5c.6 5.6 4.9 9.9 10.5 10.5-5.6.6-9.9 4.9-10.5 10.5C11.4 16.9 7.1 12.6 1.5 12 7.1 11.4 11.4 7.1 12 1.5Z" />
    </svg>
  )
}

export function OpenAILogo(props: LogoProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden {...props}>
      {[0, 60, 120].map((angle) => <ellipse key={angle} cx="12" cy="12" rx="4" ry="9" transform={`rotate(${angle} 12 12)`} />)}
    </svg>
  )
}

export const PROVIDER_LOGOS: Record<LlmProvider, ComponentType<LogoProps>> = { gemini: GeminiLogo, openai: OpenAILogo }
