import { Component, type ErrorInfo, type ReactNode } from "react"
import { ErrorScreen } from "@/components/patterns/error-screen"

/** Last line of defence: a crash anywhere below it shows the error screen with a reload action. Never retries by itself. */
export class ErrorBoundary extends Component<{ children: ReactNode }, { error: unknown }> {
  state: { error: unknown } = { error: null }

  static getDerivedStateFromError(error: unknown) {
    return { error: error ?? new Error("Unknown error") }
  }

  componentDidCatch(error: unknown, info: ErrorInfo) {
    if (import.meta.env.DEV) console.error(error, info.componentStack)
  }

  render() {
    return this.state.error ? <ErrorScreen error={this.state.error} className="min-h-svh" /> : this.props.children
  }
}
