import { SiteLayout } from "./site-layout"

export type LegalSection = { heading: string; body: string[] }

/** Long-form legal text: one column at reading width, a contents list for jumping. */
export function LegalPage({ title, updated, intro, sections }: { title: string; updated: string; intro: string; sections: LegalSection[] }) {
  const slug = (h: string) => h.toLowerCase().replace(/[^a-z0-9]+/g, "-")
  return (
    <SiteLayout>
      <div className="mx-auto grid w-full max-w-6xl gap-12 px-4 py-16 sm:px-6 lg:grid-cols-[14rem_minmax(0,1fr)]">
        <nav aria-label="On this page" className="hidden lg:block">
          <ul className="sticky top-24 space-y-2 text-sm text-muted-foreground">
            {sections.map((s) => <li key={s.heading}><a href={`#${slug(s.heading)}`} className="hover:text-foreground">{s.heading}</a></li>)}
          </ul>
        </nav>
        <article className="max-w-prose">
          <h1 className="font-display text-4xl font-semibold tracking-tight">{title}</h1>
          <p className="mt-3 text-sm text-muted-foreground">Last updated {updated}</p>
          <p className="mt-8 text-pretty">{intro}</p>
          {sections.map((s) => (
            <section key={s.heading} id={slug(s.heading)} className="mt-10 scroll-mt-24">
              <h2 className="text-lg font-semibold">{s.heading}</h2>
              {s.body.map((p) => <p key={p} className="mt-3 text-pretty text-muted-foreground">{p}</p>)}
            </section>
          ))}
        </article>
      </div>
    </SiteLayout>
  )
}
