import { toast } from "sonner"
import { StatusBanner } from "@/components/patterns/status-banner"
import { UsageMeter } from "@/components/patterns/usage-meter"
import { Button } from "@/components/ui/button"
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty"
import { Skeleton } from "@/components/ui/skeleton"
import { ArrowsClockwise, ArrowUUpLeft, CheckCircle, Info, Plus, Tray, Warning, XCircle } from "@/icons"
import { Section, Specimen } from "../section"

export function Feedback() {
  return (
    <Section id="feedback" title="Feedback and states" intro="Banners are flat rows with an icon, not boxed alerts. Every list has loading, empty and error states, and errors name the problem and the recovery.">
      <div className="grid gap-10 lg:grid-cols-2">
        <Specimen title="Banners">
          <div className="space-y-3">
            <StatusBanner tone="info" title="Gmail sync is catching up.">New mail appears in a few minutes.</StatusBanner>
            <StatusBanner tone="warning" title="3 messages need review." action={<Button size="xs" variant="outline">Review</Button>}>They could not be matched to a ticket.</StatusBanner>
            <StatusBanner tone="danger" title="Gmail is disconnected." action={<Button size="xs" variant="outline" icon={<ArrowsClockwise />} data-icon-motion="turn">Reconnect</Button>}>Replies will not send until you reconnect.</StatusBanner>
          </div>
        </Specimen>
        <Specimen title="Toasts" note="Click to trigger. Icon and color match the banners.">
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" icon={<CheckCircle weight="fill" />} onClick={() => toast.success("Ticket resolved")}>Success</Button>
            <Button variant="outline" icon={<Info weight="fill" />} onClick={() => toast.info("Reply drafted", { description: "Review it before sending." })}>Info</Button>
            <Button variant="outline" icon={<Warning weight="fill" />} onClick={() => toast.warning("Storage almost full", { description: "46 of 50 MB used." })}>Warning</Button>
            <Button variant="outline" icon={<XCircle weight="fill" />} onClick={() => toast.error("Could not send", { description: "Check your connection.", action: { label: "Retry", onClick: () => {} } })}>Danger</Button>
            <Button variant="outline" icon={<ArrowUUpLeft />} onClick={() => toast.success("Ticket closed", { action: { label: "Undo", onClick: () => {} } })}>With undo</Button>
          </div>
        </Specimen>
        <Specimen title="Loading" note="Skeleton matches the row it replaces">
          <div className="space-y-3 rounded-lg border p-4" aria-busy="true">
            {[0, 1, 2].map((i) => (
              <div key={i} className="flex items-center gap-3"><Skeleton className="size-5 rounded-full" /><Skeleton className="h-4 flex-1" /><Skeleton className="h-5 w-16" /></div>
            ))}
          </div>
        </Specimen>
        <Specimen title="Usage meter" note="Knowledge-base upload quota">
          <UsageMeter label="Knowledge base storage" used={46} limit={50} format={(n) => `${n} MB`} />
        </Specimen>
      </div>
      <Specimen title="Empty state">
        <div className="rounded-lg border">
          <Empty>
            <EmptyHeader>
              <EmptyMedia variant="icon"><Tray weight="duotone" /></EmptyMedia>
              <EmptyTitle>No tickets yet</EmptyTitle>
              <EmptyDescription>New tickets from email and the portal show up here. Empty states always offer the next action.</EmptyDescription>
            </EmptyHeader>
            <EmptyContent><Button icon={<Plus weight="bold" />}>New Ticket</Button></EmptyContent>
          </Empty>
        </div>
      </Specimen>
    </Section>
  )
}
