import { useNavigate } from '@tanstack/react-router'
import { useEffect } from 'react'

const TARGETS: Record<string, string> = { d: '', t: '/tickets', k: '/knowledge', m: '/members' }

const isTyping = (target: EventTarget | null) => {
  const el = target as HTMLElement | null
  return !!el && (el.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName))
}

/** "G then D/T/K/M" jumps between the main pages of a workspace (listed in the shortcuts dialog). */
export function useGoShortcuts(workspaceId: string | undefined) {
  const navigate = useNavigate()
  useEffect(() => {
    if (!workspaceId) return
    let armedAt = 0
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey || isTyping(e.target)) return
      const key = e.key.toLowerCase()
      if (key === 'g') {
        armedAt = Date.now()
        return
      }
      if (armedAt && Date.now() - armedAt < 1200 && key in TARGETS) {
        armedAt = 0
        void navigate({ to: `/app/${workspaceId}${TARGETS[key]}` as never })
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [workspaceId, navigate])
}
