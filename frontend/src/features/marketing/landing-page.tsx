import { useRef } from "react"
import { Link } from "@tanstack/react-router"
import { Button } from "@/components/ui/button"
import { ArrowRight } from "@/icons"
import { EASE, gsap, reducedMotion, useGSAP } from "@/motion"
import { GoogleButton } from "./google-button"
import { InboxFragment, KnowledgeFragment, PortalFragment, TicketFragment } from "./product-fragments"
import { SiteLayout } from "./site-layout"

export function LandingPage() {
  const rows = useRef<HTMLUListElement>(null)
  /** The page's one authored moment: the queue settles in row by row, so the first thing seen is a working desk. */
  useGSAP(() => {
    if (reducedMotion() || !rows.current) return
    gsap.from(rows.current.querySelectorAll("[data-row]"), { y: 10, opacity: 0, duration: 0.55, ease: EASE, stagger: 0.07, delay: 0.15 })
  }, { scope: rows })

  return (
    <SiteLayout>
      <section className="mx-auto w-full max-w-6xl px-4 pt-16 pb-14 sm:px-6 sm:pt-24">
        <h1 className="max-w-3xl font-display text-4xl leading-[1.05] font-semibold tracking-tight text-balance sm:text-6xl">
          Answer every customer before the clock does.
        </h1>
        <p className="mt-5 max-w-xl text-lg text-muted-foreground text-pretty">
          ResolveAI is a support desk for small teams. Customers file tickets in your portal or by email, and your team sees what is late, who owns it and what to answer next.
        </p>
        <div className="mt-8 flex flex-wrap items-center gap-3">
          <GoogleButton size="lg">Get started with Google</GoogleButton>
          <Button size="lg" variant="ghost" iconEnd={<ArrowRight weight="bold" />} render={<a href="#how" />}>See how it works</Button>
        </div>
        <p className="mt-4 text-sm text-muted-foreground">
          Already have a desk? <Link to="/login" className="text-foreground underline underline-offset-4">Sign in</Link>
        </p>
      </section>

      <section className="bg-primary px-4 py-12 sm:px-6 sm:py-16">
        <div className="mx-auto max-w-5xl"><InboxFragment rowsRef={rows} /></div>
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
          body="Turn a good reply into an article. Agents search the knowledge base while they answer, and the next customer with the same question finds it first."
          fragment={<KnowledgeFragment />}
        />
      </section>

      <section className="border-t">
        <div className="mx-auto flex w-full max-w-6xl flex-col items-start gap-6 px-4 py-20 sm:px-6">
          <h2 className="max-w-2xl font-display text-3xl font-semibold tracking-tight text-balance sm:text-4xl">Open your desk and answer the first ticket today.</h2>
          <div className="flex flex-wrap items-center gap-3">
            <GoogleButton size="lg">Get started with Google</GoogleButton>
            <Button size="lg" variant="outline" slide={false} render={<Link to="/login" />}>Sign in</Button>
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
