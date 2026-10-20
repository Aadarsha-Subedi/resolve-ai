import { Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator } from "@/components/ui/breadcrumb"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { PageHeader } from "@/components/patterns/page-header"
import { DownloadSimple, Plus } from "@/icons"
import { Section, Specimen } from "../section"

export function Navigation() {
  return (
    <Section id="navigation" title="Navigation and page frame" intro="The frame is flat: an icon rail that expands to labels, and a hairline top bar with the breadcrumb, actions and account.">
      <Specimen title="Page header" note="Display type only here; one primary action on the right">
        <div className="rounded-lg border p-4">
          <PageHeader
            title="Tickets"
            description="Everything customers have asked, across email, chat and the portal."
            actions={<><Button variant="outline" icon={<DownloadSimple />} data-icon-motion="drop">Export</Button><Button icon={<Plus weight="bold" />} data-icon-motion="spin">New Ticket</Button></>}
          />
        </div>
      </Specimen>
      <div className="grid gap-10 lg:grid-cols-2">
        <Specimen title="Breadcrumb">
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem><BreadcrumbLink href="#navigation">Workspace</BreadcrumbLink></BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem><BreadcrumbPage>Tickets</BreadcrumbPage></BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>
        </Specimen>
        <Specimen title="Tabs">
          <Tabs defaultValue="all">
            <TabsList variant="line">
              <TabsTrigger value="all">All</TabsTrigger>
              <TabsTrigger value="mine">Assigned to me</TabsTrigger>
              <TabsTrigger value="unassigned">Unassigned</TabsTrigger>
            </TabsList>
            <TabsContent value="all" className="pt-2 text-sm text-muted-foreground">Every ticket in the workspace.</TabsContent>
            <TabsContent value="mine" className="pt-2 text-sm text-muted-foreground">Tickets you own.</TabsContent>
            <TabsContent value="unassigned" className="pt-2 text-sm text-muted-foreground">Waiting for an agent.</TabsContent>
          </Tabs>
        </Specimen>
      </div>
      <Specimen title="App frame" note="Sidebar rail, top bar, account menu, theme toggle, notifications. Opens as its own page so it can use the full viewport.">
        <Button variant="outline" nativeButton={false} render={<a href="/design-preview/frame" />}>Open the app frame</Button>
      </Specimen>
    </Section>
  )
}
