import { Button } from "@/components/ui/button"
import { ButtonGroup } from "@/components/ui/button-group"
import { Kbd } from "@/components/ui/kbd"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { ArrowRight, Check, DotsThree, DownloadSimple, Funnel, Kanban, Plus, Rows, Trash } from "@/icons"
import { Section, Specimen } from "../section"

const VARIANTS = ["default", "secondary", "outline", "ghost", "destructive", "link"] as const

export function Actions() {
  return (
    <Section id="actions" title="Buttons" intro="Every state side by side; a real screen has one primary button. Icon-only buttons need a label, which becomes the tooltip and accessible name.">
      <Specimen title="Variants" note="default · with trailing icon · disabled · loading · icon only">
        <div className="divide-y rounded-lg border">
          {VARIANTS.map((v) => (
            <div key={v} className="grid items-center gap-3 px-4 py-3 sm:grid-cols-[6rem_1fr]">
              <span className="text-xs text-muted-foreground">{v}</span>
              <div className="flex flex-wrap items-center gap-2">
                <Button variant={v} icon={v === "destructive" ? <Trash /> : <Check weight="bold" />}>{v === "destructive" ? "Delete ticket" : "Resolve"}</Button>
                <Button variant={v} iconEnd={<ArrowRight weight="bold" />}>{v === "destructive" ? "Review impact" : "Open ticket"}</Button>
                <Button variant={v} disabled icon={<Check weight="bold" />}>Disabled</Button>
                <Button variant={v} loading>Saving</Button>
                <Button variant={v} size="icon" label="More options"><DotsThree weight="bold" /></Button>
              </div>
            </div>
          ))}
        </div>
      </Specimen>
      <div className="grid gap-10 lg:grid-cols-2">
        <Specimen title="Sizes">
          <div className="flex flex-wrap items-center gap-2">
            {(["xs", "sm", "default", "lg"] as const).map((s) => <Button key={s} size={s} icon={<Plus weight="bold" />}>{s}</Button>)}
          </div>
        </Specimen>
        <Specimen title="With shortcut hint">
          <div className="flex flex-wrap items-center gap-2">
            <Button icon={<Plus weight="bold" />}>New Ticket <Kbd className="ml-1 border-black/15 bg-black/5 text-primary-foreground shadow-none">C</Kbd></Button>
            <Button variant="outline" icon={<Funnel />}>Filter <Kbd className="ml-1">F</Kbd></Button>
          </div>
        </Specimen>
        <Specimen title="Button group">
          <ButtonGroup>
            <Button slide={false} variant="outline" icon={<DownloadSimple />}>Export</Button>
            <Button slide={false} variant="outline" icon={<Funnel />}>Filter</Button>
            <Button variant="outline" size="icon" label="More"><DotsThree weight="bold" /></Button>
          </ButtonGroup>
        </Specimen>
        <Specimen title="View switch" note="Board or table, as in the reference toolbar">
          <ToggleGroup variant="outline" defaultValue={["table"]}>
            <ToggleGroupItem value="board" aria-label="Board"><Kanban /></ToggleGroupItem>
            <ToggleGroupItem value="table" aria-label="Table"><Rows /></ToggleGroupItem>
          </ToggleGroup>
        </Specimen>
      </div>
    </Section>
  )
}
