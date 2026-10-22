import { useMemo, useState } from "react"
import { Assignee } from "@/components/patterns/assignee"
import { DataTable, SortHeader, TableOptionsMenu, selectColumn, type DataColumn } from "@/components/patterns/data-table"
import { FilterBar } from "@/components/patterns/filter-bar"
import { StatCard } from "@/components/patterns/stat-card"
import { ChannelLabel, HealthBadge, PriorityLabel, STATUS_OPTIONS, TicketStatusBadge } from "@/components/patterns/ticket-meta"
import { Button } from "@/components/ui/button"
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty"
import { Pagination, PaginationContent, PaginationItem, PaginationNext, PaginationPrevious } from "@/components/ui/pagination"
import { CheckCircle, CircleHalf, Clock, DotsThree, Tray, Ticket, Trash, UserSwitch } from "@/icons"
import { TICKETS, type Ticket as TicketRow } from "../data"
import { Section, Specimen } from "../section"

const columns: DataColumn<TicketRow>[] = [
  selectColumn<TicketRow>(),
  { accessorKey: "number", header: ({ column }) => <SortHeader label="ID" column={column} />, meta: { label: "ID" }, cell: ({ row }) => <span className="tabular-nums text-muted-foreground">#-{String(row.original.number).padStart(3, "0")}</span> },
  { accessorKey: "subject", header: ({ column }) => <SortHeader label="Subject" column={column} />, meta: { label: "Subject" }, cell: ({ row }) => <span className="font-medium" title={row.original.subject}>{row.original.subject}</span> },
  { accessorKey: "status", header: ({ column }) => <SortHeader label="Status" column={column} />, meta: { label: "Status" }, cell: ({ row }) => <TicketStatusBadge status={row.original.status} /> },
  { accessorKey: "priority", header: "Priority", cell: ({ row }) => <PriorityLabel priority={row.original.priority} /> },
  { accessorKey: "assignee", header: "Assignee", cell: ({ row }) => <Assignee name={row.original.assignee} /> },
  { accessorKey: "category", header: "Category" },
  { accessorKey: "channel", header: "Channel", cell: ({ row }) => <ChannelLabel channel={row.original.channel} /> },
  { accessorKey: "health", header: "Health", cell: ({ row }) => <HealthBadge health={row.original.health} /> },
  { id: "actions", enableHiding: false, header: () => <span className="sr-only">Actions</span>, cell: () => <Button variant="ghost" size="icon-sm" label="Row actions" data-icon-motion="lift"><DotsThree weight="bold" /></Button> },
]

export function DataSection() {
  const [status, setStatus] = useState<string | undefined>()
  const [q, setQ] = useState("")
  const data = useMemo(
    () => TICKETS.filter((t) => (!status || t.status === status) && (!q || `${t.subject} ${t.number}`.toLowerCase().includes(q.toLowerCase()))),
    [status, q],
  )
  return (
    <Section id="data" title="Tickets and metrics" intro="The reference screen as components: stat cards, toolbar, a dense TanStack table with sorting, selection and column options. Status, priority, channel and health use one vocabulary.">
      <Specimen title="Stat cards" note="Number, trend with direction and meaning, skeleton while loading">
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Total tickets" value={20} icon={<Ticket className="size-3.5" />} trend={{ change: 3, percent: "17.6%", good: false }} />
          <StatCard label="Open" value={8} icon={<Tray className="size-3.5" />} trend={{ change: -2, percent: "20%", good: true }} />
          <StatCard label="Pending" value={5} icon={<Clock className="size-3.5" />} trend={{ change: -1, percent: "16.7%", good: true }} />
          <StatCard label="Resolved" value={4} icon={<CheckCircle className="size-3.5" />} loading />
        </div>
      </Specimen>
      <Specimen title="Ticket table" note="Sort by header, tick rows for the bulk bar, hide columns in Table options, filter and search above">
        <DataTable
          columns={columns}
          data={data}
          getRowId={(r) => r.id}
          caption="Tickets, sortable by column"
          empty={
            <Empty>
              <EmptyHeader>
                <EmptyMedia variant="icon"><Tray weight="duotone" /></EmptyMedia>
                <EmptyTitle>No tickets match</EmptyTitle>
                <EmptyDescription>Clear the filter or search to see every ticket.</EmptyDescription>
              </EmptyHeader>
              <EmptyContent><Button variant="outline" onClick={() => { setStatus(undefined); setQ("") }}>Clear filters</Button></EmptyContent>
            </Empty>
          }
          toolbar={(table) => {
            const selected = table.getSelectedRowModel().rows.length
            return (
              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  <FilterBar
                    search={{ value: q, onCommit: (v) => setQ(v ?? ""), placeholder: "Search tickets by subject, customer, or ID" }}
                    filters={[{ id: "status", kind: "select", label: "Status", icon: CircleHalf, options: STATUS_OPTIONS, value: status, onChange: setStatus }]}
                    onClearAll={() => { setStatus(undefined); setQ("") }}
                    trailing={<span className="ml-auto"><TableOptionsMenu table={table} /></span>}
                  />
                </div>
                <div className="flex h-9 items-center gap-2 text-sm" aria-live="polite">
                  {selected ? (
                    <>
                      <span className="font-medium">{selected} selected</span>
                      <Button size="xs" variant="outline" icon={<UserSwitch />}>Assign</Button>
                      <Button size="xs" variant="destructive" icon={<Trash />}>Delete</Button>
                    </>
                  ) : (
                    <span className="text-muted-foreground tabular-nums">{data.length} tickets</span>
                  )}
                </div>
              </div>
            )
          }}
          footer={
            <Pagination className="justify-end">
              <PaginationContent>
                <PaginationItem><PaginationPrevious href="#data" /></PaginationItem>
                <PaginationItem><PaginationNext href="#data" /></PaginationItem>
              </PaginationContent>
            </Pagination>
          }
        />
      </Specimen>
      <Specimen title="Loading" note="Skeleton rows replace the table body, same row height">
        <DataTable columns={columns} data={[]} getRowId={(r) => r.id} caption="Loading tickets" loading />
      </Specimen>
    </Section>
  )
}
