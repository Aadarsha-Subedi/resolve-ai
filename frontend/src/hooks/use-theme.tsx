import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react"

export type Theme = "system" | "light" | "dark"

interface ThemeState {
  theme: Theme
  resolved: "light" | "dark"
  setTheme: (t: Theme) => void
}

const KEY = "resolveai-ui-prefs"
const defaults = { theme: "system" as Theme }

function load() {
  try {
    return { ...defaults, ...JSON.parse(localStorage.getItem(KEY) ?? "{}") }
  } catch {
    return defaults
  }
}

const Ctx = createContext<ThemeState | null>(null)

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [prefs, setPrefs] = useState(load)
  const [systemDark, setSystemDark] = useState(() => window.matchMedia("(prefers-color-scheme: dark)").matches)

  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)")
    const on = () => setSystemDark(mq.matches)
    mq.addEventListener("change", on)
    return () => mq.removeEventListener("change", on)
  }, [])

  const resolved = prefs.theme === "system" ? (systemDark ? "dark" : "light") : prefs.theme

  useEffect(() => {
    const el = document.documentElement
    el.classList.toggle("dark", resolved === "dark")
    try {
      localStorage.setItem(KEY, JSON.stringify(prefs))
    } catch {
      /* storage unavailable */
    }
  }, [resolved, prefs])

  const value = useMemo<ThemeState>(
    () => ({
      ...prefs,
      resolved,
      setTheme: (theme) => setPrefs((p: typeof prefs) => ({ ...p, theme })),
    }),
    [prefs, resolved],
  )
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useTheme() {
  const v = useContext(Ctx)
  if (!v) throw new Error("useTheme outside ThemeProvider")
  return v
}
