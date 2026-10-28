import { useNavigate } from '@tanstack/react-router'
import { useRef, useState, type FormEvent } from 'react'
import { toast } from 'sonner'

import { ConfirmDialog } from '@/components/patterns/confirm-dialog'
import { PageHeader } from '@/components/patterns/page-header'
import { Restricted } from '@/components/patterns/restricted'
import { Button } from '@/components/ui/button'
import { Field, FieldError } from '@/components/ui/field'
import { SettingGroup, SettingRow } from '@/components/patterns/setting-row'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { AiSettings } from '@/features/ai/ai-settings'
import { OWNER_ONLY, useWorkspace } from '@/features/app/workspace-context'
import { WorkspaceMark } from '@/features/app/workspace-mark'
import { ManageCategoriesDialog } from '@/features/knowledge/category-controls'
import { useDeleteWorkspace, useRemoveLogo, useResetDemo, useUpdateWorkspace, useUploadLogo } from '@/features/workspaces/api'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { ArrowCounterClockwise, Copy, FloppyDisk, ImageSquare, Tag, Trash } from '@/icons'
import { errorMessage, fieldError } from '@/lib/api'

const LOGO_TYPES = ['image/png', 'image/jpeg', 'image/webp']
const LOGO_MAX = 2 * 1024 * 1024

export function SettingsPage() {
  useDocumentTitle('Settings · ResolveAI')
  const { workspace, isOwner } = useWorkspace()
  const navigate = useNavigate()
  const update = useUpdateWorkspace(workspace.id)
  const uploadLogo = useUploadLogo(workspace.id)
  const removeLogo = useRemoveLogo(workspace.id)
  const deleteWorkspace = useDeleteWorkspace(workspace.id)
  const resetDemo = useResetDemo(workspace.id)
  const fileInput = useRef<HTMLInputElement>(null)
  const [name, setName] = useState(workspace.name)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [managingCategories, setManagingCategories] = useState(false)
  const lock = isOwner ? null : OWNER_ONLY
  const portalUrl = `${window.location.origin}/portal/${workspace.slug}`

  const saveName = (event: FormEvent) => {
    event.preventDefault()
    update.mutate({ name: name.trim() }, { onSuccess: () => toast.success('Workspace renamed.'), onError: (e) => !fieldError(e, 'name') && toast.error(errorMessage(e)) })
  }
  const pickLogo = (file: File | undefined) => {
    if (!file) return
    if (!LOGO_TYPES.includes(file.type)) return void toast.error('Use a PNG, JPEG or WebP image.')
    if (file.size > LOGO_MAX) return void toast.error('The logo can be at most 2 MB.')
    uploadLogo.mutate(file, { onSuccess: () => toast.success('Logo updated.'), onError: (e) => toast.error(errorMessage(e)) })
  }

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <PageHeader title="Settings" description={`Manage ${workspace.name}.`} />

      <SettingGroup id="general" title="General">
        <SettingRow title="Workspace name" htmlFor="s-name" description="Shown in the workspace switcher and on the portal.">
          <form onSubmit={saveName} className="flex flex-wrap items-start gap-2">
            <Field className="w-64 max-w-full">
              <Input id="s-name" value={name} maxLength={80} disabled={!isOwner} onChange={(e) => setName(e.target.value)} aria-invalid={!!fieldError(update.error, 'name')} />
              <FieldError>{fieldError(update.error, 'name')}</FieldError>
            </Field>
            <Restricted reason={lock}>
              <Button type="submit" variant="outline" icon={<FloppyDisk />} loading={update.isPending && !!update.variables?.name} disabled={!name.trim() || name.trim() === workspace.name}>Save</Button>
            </Restricted>
          </form>
        </SettingRow>
        <SettingRow title="Logo" description="PNG, JPEG or WebP, up to 2 MB. It appears in the workspace switcher and on the portal.">
          <WorkspaceMark workspace={workspace} size="lg" />
          <input ref={fileInput} type="file" accept="image/png,image/jpeg,image/webp" className="sr-only" aria-label="Choose a logo image" onChange={(e) => { pickLogo(e.target.files?.[0]); e.target.value = '' }} />
          <Restricted reason={lock}>
            <Button variant="outline" icon={<ImageSquare />} loading={uploadLogo.isPending} onClick={() => fileInput.current?.click()}>{workspace.logo_url ? 'Replace' : 'Upload'}</Button>
          </Restricted>
          {workspace.logo_url && (
            <Restricted reason={lock}>
              <Button variant="ghost" icon={<Trash />} loading={removeLogo.isPending} onClick={() => removeLogo.mutate(undefined, { onSuccess: () => toast.success('Logo removed.'), onError: (e) => toast.error(errorMessage(e)) })}>Remove</Button>
            </Restricted>
          )}
        </SettingRow>
      </SettingGroup>

      <SettingGroup id="portal" title="Customer portal">
        <SettingRow title="Accept tickets through the portal" htmlFor="s-portal" description={workspace.portal_enabled ? 'Customers can open tickets from the public portal.' : 'The portal is off, so visitors see a not-found page.'}>
          <Restricted reason={lock}>
            <Switch id="s-portal" checked={workspace.portal_enabled} onCheckedChange={(on) => update.mutate({ portal_enabled: on }, { onSuccess: () => toast.success(on ? 'Portal enabled.' : 'Portal disabled.'), onError: (e) => toast.error(errorMessage(e)) })} />
          </Restricted>
        </SettingRow>
        <SettingRow title="Portal address" htmlFor="s-portal-url" description="The address is permanent.">
          <div className="flex w-full gap-2 sm:w-80">
            <Input id="s-portal-url" readOnly value={portalUrl} onFocus={(e) => e.currentTarget.select()} />
            <Button variant="outline" icon={<Copy />} onClick={() => void navigator.clipboard.writeText(portalUrl).then(() => toast.success('Address copied.'), () => toast.error('Copy failed. Select the text and copy it.'))}>Copy</Button>
          </div>
        </SettingRow>
      </SettingGroup>

      <SettingGroup id="knowledge" title="Knowledge base">
        <SettingRow title="Categories" description="Group articles and files. Renaming or deleting a category never deletes the content filed under it.">
          <Button variant="outline" icon={<Tag />} onClick={() => setManagingCategories(true)}>Manage categories</Button>
        </SettingRow>
      </SettingGroup>

      <AiSettings workspaceId={workspace.id} isOwner={isOwner} />

      <SettingGroup id="danger" title="Danger zone">
        {workspace.is_demo && (
          <SettingRow danger title="Reset demo" description="Replaces every ticket with the original sample tickets. Your changes to them are lost.">
            <Restricted reason={lock}>
              <Button variant="outline" icon={<ArrowCounterClockwise />} loading={resetDemo.isPending} onClick={() => resetDemo.mutate(undefined, { onSuccess: () => toast.success('Demo reset to its sample tickets.'), onError: (e) => toast.error(errorMessage(e)) })}>Reset demo</Button>
            </Restricted>
          </SettingRow>
        )}
        <SettingRow danger title="Delete workspace" description="Everyone loses access immediately. The workspace and its tickets are removed after a grace period.">
          <Restricted reason={lock}>
            <Button variant="destructive" icon={<Trash />} onClick={() => setConfirmDelete(true)}>Delete workspace</Button>
          </Restricted>
        </SettingRow>
      </SettingGroup>
      <ManageCategoriesDialog workspaceId={workspace.id} open={managingCategories} onOpenChange={setManagingCategories} />
      <ConfirmDialog
          open={confirmDelete}
          onOpenChange={setConfirmDelete}
          title={`Delete ${workspace.name}?`}
          description="All members lose access straight away. Its tickets, articles and files are purged after the grace period."
          confirmLabel="Delete workspace"
          destructive
          onConfirm={() =>
            deleteWorkspace.mutate(undefined, {
              onSuccess: (message) => {
                toast.success(message)
                void navigate({ to: '/app' })
              },
              onError: (e) => toast.error(errorMessage(e)),
            })
          }
        />
    </div>
  )
}
