import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea"
import { OptionSelect } from "@/components/patterns/option-select"
import { FilterSelect } from "@/components/patterns/filter-select"
import { SearchBox } from "@/components/patterns/search-box"
import { PRIORITY_OPTIONS, STATUS_OPTIONS } from "@/components/patterns/ticket-meta"
import { CreditCard, EnvelopeSimple, FloppyDisk, UserCircle, Wrench } from "@/icons"
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
      <Specimen title="Search and filters" note="The toolbar controls from the reference: debounced search plus filter dropdowns. A filter shows its name until a value is chosen, then only the value; the first choice clears it.">
        <div className="flex flex-wrap items-center gap-2 rounded-lg border p-3">
          <SearchBox value={q} onCommit={(v) => setQ(v ?? "")} placeholder="Search tickets by subject, customer, or ID" />
          <FilterSelect label="Status" value={status} onChange={setStatus} options={STATUS_OPTIONS} />
          <FilterSelect label="Priority" value={priority} onChange={setPriority} options={PRIORITY_OPTIONS} />
          <span className="text-xs text-muted-foreground" aria-live="polite">{q ? `Searching “${q}”` : "No search"}</span>
        </div>
      </Specimen>
    </Section>
  )
}
