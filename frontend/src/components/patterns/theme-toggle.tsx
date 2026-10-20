import { Button } from "@/components/ui/button"
import { Desktop, Moon, Sun } from "@/icons"
import { useTheme, type Theme } from "@/hooks/use-theme"

const ORDER: Theme[] = ["light", "dark", "system"]
const ICON = { light: Sun, dark: Moon, system: Desktop } as const
const NAME = { light: "Light", dark: "Dark", system: "System" } as const

/** One button that steps through light, dark and system. The icon shows the current choice; the label names it and the next. */
export function ThemeToggle() {
  const { theme, setTheme } = useTheme()
  const next = ORDER[(ORDER.indexOf(theme) + 1) % ORDER.length]
  const Icon = ICON[theme]
  return (
    <Button variant="outline" size="icon" label={`Theme: ${NAME[theme]}. Switch to ${NAME[next]}`} onClick={() => setTheme(next)}>
      <Icon />
    </Button>
  )
}
