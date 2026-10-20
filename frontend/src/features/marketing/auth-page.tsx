import { useState } from "react"
import { Link } from "@tanstack/react-router"
import { Logo } from "@/components/patterns/logo"
import { Checkbox } from "@/components/ui/checkbox"
import { Field, FieldLabel } from "@/components/ui/field"
import { WarningOctagon } from "@/icons"
import { GOOGLE_ERROR_MESSAGES } from "@/features/auth/api"
import { GoogleButton } from "./google-button"
import { InboxFragment } from "./product-fragments"

const COPY = {
  login: {
    title: "Welcome back",
    body: "Sign in with the Google account your workspace uses.",
    cta: "Sign in with Google",
    alt: { text: "New to ResolveAI?", label: "Create an account", to: "/signup" as const },
  },
  signup: {
    title: "Create your support desk",
    body: "Continue with Google to create your account. You can invite your team and connect Gmail after.",
    cta: "Sign up with Google",
    alt: { text: "Already have an account?", label: "Sign in", to: "/login" as const },
  },
}

/** Sign-in and sign-up are the same Google flow; only the words differ. The right panel shows the product on the brand field. */
export function AuthPage({ mode, error }: { mode: "login" | "signup"; error?: string }) {
  const c = COPY[mode]
  const [remember, setRemember] = useState(false)
  const errorText = error ? (GOOGLE_ERROR_MESSAGES[error] ?? GOOGLE_ERROR_MESSAGES.google_failed) : undefined
  return (
    <div className="grid min-h-svh lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
      <div className="flex flex-col px-6 py-8 sm:px-12">
        <Link to="/" aria-label="ResolveAI home" className="w-fit"><Logo /></Link>
        <div className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center gap-6 py-12">
          <div className="space-y-2">
            <h1 className="font-display text-3xl font-semibold tracking-tight text-balance">{c.title}</h1>
            <p className="text-muted-foreground text-pretty">{c.body}</p>
          </div>
          {errorText && (
            <p role="alert" className="flex items-start gap-2 text-sm text-danger-text">
              <WarningOctagon weight="fill" className="mt-0.5 size-4 shrink-0" aria-hidden />
              {errorText}
            </p>
          )}
          <Field orientation="horizontal">
            <Checkbox id="remember" checked={remember} onCheckedChange={(v) => setRemember(v === true)} />
            <FieldLabel htmlFor="remember">Keep me signed in on this device</FieldLabel>
          </Field>
          <GoogleButton size="lg" className="w-fit" remember={remember}>{c.cta}</GoogleButton>
          <p className="text-sm text-muted-foreground">
            By continuing you agree to the <Link to="/terms" className="text-foreground underline underline-offset-4">Terms</Link> and <Link to="/privacy" className="text-foreground underline underline-offset-4">Privacy Policy</Link>.
          </p>
          <p className="text-sm text-muted-foreground">
            {c.alt.text} <Link to={c.alt.to} className="text-foreground underline underline-offset-4">{c.alt.label}</Link>
          </p>
        </div>
      </div>
      <div className="hidden items-center bg-primary p-12 lg:flex">
        <div className="w-full"><InboxFragment /></div>
      </div>
    </div>
  )
}
