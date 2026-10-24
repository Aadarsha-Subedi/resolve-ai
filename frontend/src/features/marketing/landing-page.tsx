import { Link } from "@tanstack/react-router"
import { Button } from "@/components/ui/button"
import { GOOGLE_ERROR_MESSAGES } from "@/features/auth/api"
import { ArrowRight, WarningOctagon } from "@/icons"
import { GoogleButton } from "./google-button"
import { HeroDemo } from "./hero-demo"
import { KnowledgeFragment, PortalFragment, TicketFragment } from "./product-fragments"
import { Screenshot } from "./screenshot"
import { SiteLayout } from "./site-layout"

export function LandingPage({ error }: { error?: string }) {
  const errorText = error ? (GOOGLE_ERROR_MESSAGES[error] ?? GOOGLE_ERROR_MESSAGES.google_failed) : undefined
  return (
    <SiteLayout>
      {errorText && (
        <p role="alert" className="mx-auto mt-6 flex w-full max-w-6xl items-start gap-2 px-4 text-sm text-danger-text sm:px-6">
          <WarningOctagon weight="fill" className="mt-0.5 size-4 shrink-0" aria-hidden />
          {errorText}
        </p>
      )}
      <section className="mx-auto grid w-full max-w-6xl items-center gap-12 px-4 pt-14 pb-20 sm:px-6 sm:pt-20 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)] lg:gap-14 lg:pb-28">
        <div>
          <h1 className="font-display text-4xl leading-[1.05] font-semibold tracking-tight text-balance sm:text-5xl lg:text-[3.5rem]">
            Every customer answered before the clock runs out.
          </h1>
          <p className="mt-5 max-w-xl text-lg text-muted-foreground text-pretty">
            A support desk for small teams. Tickets arrive from your portal or Gmail, AI drafts the reply from your own documents, and a person always reviews and sends.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <GoogleButton size="lg">Start free with Google</GoogleButton>
            <Button size="lg" variant="ghost" iconEnd={<ArrowRight weight="bold" />} render={<a href="#how" />}>See how it works</Button>
          </div>
          <p className="mt-4 max-w-md text-sm text-muted-foreground">
            Your first workspace comes with sample tickets and a guided tour.
          </p>
        </div>
        <HeroDemo />
      </section>

      <section id="how" className="mx-auto flex w-full max-w-6xl scroll-mt-14 flex-col gap-24 px-4 py-24 sm:px-6">
        <Feature
          title="See what is late before a customer tells you."
          body="Every ticket carries its own clock. The queue puts breached and at-risk tickets first, with the owner, priority and channel beside them, so nobody scans the whole list to find the fire."
          fragment={<TicketFragment />}
        />
        <Feature
          reverse
          title="Customers ask where they already are."
          body="Each workspace gets a portal for new requests, and mail sent to your connected Gmail becomes a ticket too. Replies go back the same way, so customers never learn a new tool."
          fragment={<PortalFragment />}
        />
        <Feature
          title="Write the answer once."
          body="Turn a good reply into an article. Ask your desk a question and get an answer written from your own knowledge base, with its sources cited."
          fragment={<Screenshot name="knowledge" alt="The knowledge base with articles by category" fallback={<KnowledgeFragment />} />}
        />
      </section>

      <section className="border-t">
        <div className="mx-auto flex w-full max-w-6xl flex-col items-start gap-6 px-4 py-20 sm:px-6">
          <h2 className="max-w-2xl font-display text-3xl font-semibold tracking-tight text-balance sm:text-4xl">Open your desk and answer the first ticket in minutes.</h2>
          <div className="flex flex-wrap items-center gap-3">
            <GoogleButton size="lg">Get started with Google</GoogleButton>
          </div>
          <p className="max-w-md text-sm text-muted-foreground">
            You sign in with the Google account you already use. By continuing you agree to the <Link to="/terms" className="text-foreground underline underline-offset-4">Terms</Link> and <Link to="/privacy" className="text-foreground underline underline-offset-4">Privacy Policy</Link>.
          </p>
        </div>
      </section>
    </SiteLayout>
  )
}

function Feature({ title, body, fragment, reverse }: { title: string; body: string; fragment: React.ReactNode; reverse?: boolean }) {
  return (
    <div className="grid items-center gap-10 md:grid-cols-2 md:gap-16">
      <div className={reverse ? "md:order-2" : undefined}>
        <h2 className="font-display text-3xl font-semibold tracking-tight text-balance sm:text-4xl">{title}</h2>
        <p className="mt-4 max-w-md text-muted-foreground text-pretty">{body}</p>
      </div>
      <div className={reverse ? "md:order-1" : undefined}>{fragment}</div>
    </div>
  )
}
