import { useEffect } from "react"

/** Sets a descriptive page title (WCAG 2.4.2). */
export function useDocumentTitle(title: string) {
  useEffect(() => {
    document.title = title
  }, [title])
}
