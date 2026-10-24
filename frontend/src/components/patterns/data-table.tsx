import {
  columnVisibilityFeature,
  createSortedRowModel,
  flexRender,
  rowSelectionFeature,
  rowSortingFeature,
  sortFns,
  tableFeatures,
  useTable,
  type ColumnDef,
  type RowData,
} from "@tanstack/react-table"
import type { ReactNode } from "react"
import { Checkbox } from "@/components/ui/checkbox"
import { Skeleton } from "@/components/ui/skeleton"
import { Button } from "@/components/ui/button"
import { DropdownMenu, DropdownMenuCheckboxItem, DropdownMenuContent, DropdownMenuGroup, DropdownMenuLabel, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { ArrowDown, ArrowUp, CaretUpDown, SlidersHorizontal } from "@/icons"
import { cn } from "@/lib/utils"

// Module scope on purpose: TanStack Table v9 needs stable feature inputs.
const features = tableFeatures({
  rowSortingFeature,
  rowSelectionFeature,
  columnVisibilityFeature,
  sortedRowModel: createSortedRowModel(),
  sortFns,
})

export type DataColumn<T extends RowData> = ColumnDef<typeof features, T>
type DataTableApi<T extends RowData> = ReturnType<typeof useTable<typeof features, T>>

/** Sortable column header: a ghost button so it is keyboard reachable and announces its state through aria-sort on the th. */
export function SortHeader({ label, column }: { label: string; column: { getIsSorted: () => false | "asc" | "desc"; toggleSorting: (desc?: boolean) => void } }) {
  const sorted = column.getIsSorted()
  return (
    <Button
      variant="ghost"
      size="xs"
      className="-ml-2 text-muted-foreground hover:text-foreground"
      iconEnd={sorted === "asc" ? <ArrowUp weight="bold" /> : sorted === "desc" ? <ArrowDown weight="bold" /> : <CaretUpDown />}
      onClick={() => column.toggleSorting(sorted === "asc")}
    >
      {label}
    </Button>
  )
}

/** Column visibility menu ("Table options" in the reference). Needs the table instance from `toolbar`. */
export function TableOptionsMenu<T extends RowData>({ table }: { table: DataTableApi<T> }) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger render={<Button variant="outline" icon={<SlidersHorizontal />}>Table options</Button>} />
      <DropdownMenuContent align="end" className="w-48">
        <DropdownMenuGroup>
          <DropdownMenuLabel>Columns</DropdownMenuLabel>
          {table.getAllColumns().filter((c) => c.getCanHide()).map((c) => (
            <DropdownMenuCheckboxItem key={c.id} checked={c.getIsVisible()} onCheckedChange={(v) => c.toggleVisibility(!!v)}>
              {typeof c.columnDef.header === "string" ? c.columnDef.header : (c.columnDef.meta as { label?: string } | undefined)?.label ?? c.id}
            </DropdownMenuCheckboxItem>
          ))}
        </DropdownMenuGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

/** Checkbox column for row selection. */
export function selectColumn<T extends RowData>(): DataColumn<T> {
  return {
    id: "select",
    enableHiding: false,
    header: ({ table }) => <Checkbox aria-label="Select all rows" checked={table.getIsAllRowsSelected()} indeterminate={table.getIsSomeRowsSelected()} onCheckedChange={(v) => table.toggleAllRowsSelected(!!v)} />,
    cell: ({ row }) => <Checkbox aria-label="Select row" checked={row.getIsSelected()} onCheckedChange={(v) => row.toggleSelected(!!v)} onClick={(e) => e.stopPropagation()} />,
  }
}

/**
 * Dense, scannable table. Headers are sticky tone, rows are 40px with hairlines, selection tints the row.
 * `columns` and `data` must be referentially stable (module scope or useMemo).
 */
export function DataTable<T extends RowData>({ columns, data, getRowId, caption, loading, empty, onRowClick, toolbar, footer, className }: {
  columns: DataColumn<T>[]
  data: T[]
  getRowId: (row: T) => string
  /** Screen-reader caption naming the table. */
  caption: string
  loading?: boolean
  /** Shown in place of rows when there are none (use EmptyState). */
  empty?: ReactNode
  onRowClick?: (row: T) => void
  /** Rendered above the table, receives the table instance (selection count, options menu). */
  toolbar?: (table: DataTableApi<T>) => ReactNode
  footer?: ReactNode
  className?: string
}) {
  const table = useTable<typeof features, T>({ features, columns, data, getRowId })
  const rows = table.getRowModel().rows
  return (
    <div className={cn("space-y-3", className)}>
      {toolbar?.(table)}
      <div className="overflow-hidden rounded-xl border">
        <Table className="text-[0.8125rem]">
          <caption className="sr-only">{caption}</caption>
          <TableHeader className="bg-surface">
            {table.getHeaderGroups().map((group) => (
              <TableRow key={group.id} className="hover:bg-transparent">
                {group.headers.map((header) => {
                  const sorted = header.column.getIsSorted()
                  return (
                    <TableHead key={header.id} aria-sort={sorted === "asc" ? "ascending" : sorted === "desc" ? "descending" : undefined} className="h-9 text-xs font-medium text-muted-foreground">
                      {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                    </TableHead>
                  )
                })}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {loading ? (
              Array.from({ length: 6 }, (_, i) => (
                <TableRow key={i} className="h-(--row-h) hover:bg-transparent">
                  {table.getVisibleLeafColumns().map((c) => (
                    <TableCell key={c.id} className="py-0"><Skeleton className="h-4 w-full max-w-32" /></TableCell>
                  ))}
                </TableRow>
              ))
            ) : rows.length === 0 ? (
              <TableRow className="hover:bg-transparent">
                <TableCell colSpan={table.getVisibleLeafColumns().length} className="p-0">{empty}</TableCell>
              </TableRow>
            ) : (
              rows.map((row) => (
                <TableRow
                  key={row.id}
                  data-state={row.getIsSelected() ? "selected" : undefined}
                  data-flip-id={row.id}
                  className={cn("h-(--row-h)", onRowClick && "cursor-pointer")}
                  onClick={onRowClick ? () => onRowClick(row.original) : undefined}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id} className="max-w-72 truncate py-0">{flexRender(cell.column.columnDef.cell, cell.getContext())}</TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
      {footer}
    </div>
  )
}
