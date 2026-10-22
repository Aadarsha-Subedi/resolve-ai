import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea"
import { OptionSelect } from "@/components/patterns/option-select"
import type { IsoRange } from "@/components/patterns/date-picker"
import { FilterBar } from "@/components/patterns/filter-bar"
import { PRIORITY_OPTIONS, STATUS_OPTIONS } from "@/components/patterns/ticket-meta"
import { CalendarBlank, CircleHalf, Clock, CreditCard, EnvelopeSimple, FloppyDisk, Flame, UserCircle, Wrench } from "@/icons"
import { Section, Specimen } from "../section"

const CATEGORIES = [
  { value: "billing", label: "Billing", icon: CreditCard },
  { value: "technical", label: "Technical", icon: Wrench },
  { value: "account", label: "Account", icon: UserCircle },
]

export function Forms() {
  const [cat, setCat] = useState("technical")
  const [q, setQ] = useState("")
  const [status, setStatus] = useState<string | undefined>()
  const [priority, setPriority] = useState<string | undefined>()
  const [range, setRange] = useState<IsoRange>({})
  const [waiting, setWaiting] = useState<boolean | undefined>()
  return (
    <Section id="forms" title="Forms and filters" intro="Label above, hint below, error replaces the hint and names the recovery. Controls share one height so rows align.">
      <div className="grid gap-12 lg:grid-cols-2">
        <Specimen title="Fields">
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="subject">Subject</FieldLabel>
              <Input id="subject" placeholder="Short summary of the problem" />
              <FieldDescription>Shown to the customer in the confirmation email.</FieldDescription>
            </Field>
            <Field>
              <FieldLabel htmlFor="email">Customer email</FieldLabel>
              <div className="relative">
                <EnvelopeSimple className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input id="email" type="email" placeholder="name@company.com" className="pl-8" />
              </div>
            </Field>
            <Field data-invalid>
              <FieldLabel htmlFor="slug">Workspace address</FieldLabel>
              <Input id="slug" defaultValue="acme support" aria-invalid />
              <FieldError>Use lowercase letters, numbers and dashes, for example acme-support.</FieldError>
            </Field>
            <Field>
              <FieldLabel htmlFor="body">Reply</FieldLabel>
              <Textarea id="body" placeholder="Write your reply…" />
            </Field>
          </FieldGroup>
        </Specimen>
        <Specimen title="Choices">
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="cat">Category</FieldLabel>
              <OptionSelect id="cat" value={cat} onValueChange={setCat} options={CATEGORIES} />
            </Field>
            <Field>
              <FieldLabel>Visibility</FieldLabel>
              <RadioGroup defaultValue="public">
                <Field orientation="horizontal"><RadioGroupItem value="public" id="r1" /><FieldLabel htmlFor="r1">Public reply</FieldLabel></Field>
                <Field orientation="horizontal"><RadioGroupItem value="internal" id="r2" /><FieldLabel htmlFor="r2">Internal note</FieldLabel></Field>
              </RadioGroup>
            </Field>
            <Field orientation="horizontal"><Checkbox id="c1" defaultChecked /><FieldLabel htmlFor="c1">Notify the customer by email</FieldLabel></Field>
            <Field orientation="horizontal"><Switch id="s1" defaultChecked /><FieldLabel htmlFor="s1">Show the public portal</FieldLabel></Field>
            <div><Button icon={<FloppyDisk />}>Save changes</Button></div>
          </FieldGroup>
        </Specimen>
      </div>
      <Specimen title="Filter bar" note="The one filter row every table uses: search, a single Filter button listing the filters not yet applied, and a removable chip per applied filter. Choosing a filter opens its value picker; date ranges offer 7 and 30 day presets; yes/no filters are chips with no value. Clear all appears while anything is on.">
        <div className="rounded-lg border p-3">
          <FilterBar
            search={{ value: q, onCommit: (v) => setQ(v ?? ""), placeholder: "Search tickets by subject or customer" }}
            filters={[
              { id: "status", kind: "select", label: "Status", icon: CircleHalf, options: STATUS_OPTIONS, value: status, onChange: setStatus },
              { id: "priority", kind: "select", label: "Priority", icon: Flame, options: PRIORITY_OPTIONS, value: priority, onChange: setPriority },
              { id: "created", kind: "date-range", label: "Created", icon: CalendarBlank, value: range, onChange: setRange },
              { id: "waiting", kind: "boolean", label: "Waiting for reply", icon: Clock, value: waiting, onChange: setWaiting },
            ]}
            onClearAll={() => { setQ(""); setStatus(undefined); setPriority(undefined); setRange({}); setWaiting(undefined) }}
          />
        </div>
      </Specimen>
    </Section>
  )
}
