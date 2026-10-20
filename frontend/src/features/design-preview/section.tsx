import type { ReactNode } from "react"

export function Section({ id, title, intro, children }: { id: string; title: string; intro: string; children: ReactNode }) {
  return (
    <section id={id} className="scroll-mt-20 border-t py-12 first:border-t-0 first:pt-0">
      <div data-reveal className="mb-8 max-w-prose">
        <h2 className="font-display text-xl font-semibold">{title}</h2>
        <p className="mt-1.5 text-muted-foreground">{intro}</p>
      </div>
      <div className="space-y-10">{children}</div>
    </section>
  )
}

export function Specimen({ title, note, children }: { title: string; note?: string; children: ReactNode }) {
  return (
    <div data-reveal>
      <div className="mb-3">
        <h3 className="text-sm font-medium">{title}</h3>
        {note && <p className="mt-0.5 text-xs text-muted-foreground">{note}</p>}
      </div>
      {children}
    </div>
  )
}
