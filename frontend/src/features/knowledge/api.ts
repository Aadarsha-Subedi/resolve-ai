import { useMutation, useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query'

import { api, apiList, ApiError } from '@/lib/api'

export type ArticleStatus = 'draft' | 'published' | 'archived'
export type Category = { id: string; name: string; slug: string }
export type Article = {
  id: string
  title: string
  status: ArticleStatus
  categories: Category[]
  size_bytes: number
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
  published_at: string | null
  content?: string
}
export type Upload = { id: string; category: Category | null; filename: string; content_type: string; size_bytes: number; status: 'pending' | 'ready'; uploaded_by: string | null; created_at: string }
export type StorageUsage = { used_bytes: number; limit_bytes: number; remaining_bytes: number }

export const ARTICLE_PAGE_SIZE = 25
const key = (ws: string) => ['ws', ws, 'knowledge'] as const

export type ArticleFilters = { title?: string; status?: ArticleStatus; category?: string; ordering?: string; page?: number }

export function useArticles(ws: string, filters: ArticleFilters) {
  const { page = 1, ...rest } = filters
  const query = { ...rest, limit: ARTICLE_PAGE_SIZE, offset: (page - 1) * ARTICLE_PAGE_SIZE }
  return useQuery({
    queryKey: [...key(ws), 'articles', 'list', query],
    queryFn: ({ signal }) => apiList<Article>(`/workspaces/${ws}/knowledge/articles/`, query, signal),
  })
}

export const GRAPH_ARTICLE_LIMIT = 100

/** Everything the graph view draws: the newest 100 articles (the API's page maximum) and all categories. Fetched only while the view is open. */
export function useArticleGraph(ws: string, enabled: boolean) {
  const query = { limit: GRAPH_ARTICLE_LIMIT, offset: 0, ordering: '-updated_at' }
  return useQuery({
    queryKey: [...key(ws), 'articles', 'list', 'graph', query],
    enabled,
    queryFn: ({ signal }) => apiList<Article>(`/workspaces/${ws}/knowledge/articles/`, query, signal),
  })
}

function staleArticles(client: QueryClient, ws: string) {
  void client.invalidateQueries({ queryKey: [...key(ws), 'articles', 'list'], refetchType: 'none' })
}

export function useArticle(ws: string, id: string | undefined) {
  return useQuery({
    queryKey: [...key(ws), 'articles', 'detail', id],
    enabled: !!id,
    queryFn: async ({ signal }) => (await api.get<Article>(`/workspaces/${ws}/knowledge/articles/${id}/`, undefined, signal)).data,
  })
}

export type ArticleInput = { title: string; content: string; category_ids: string[] }

export function useCreateArticle(ws: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: async (body: ArticleInput) => (await api.post<Article>(`/workspaces/${ws}/knowledge/articles/`, body)).data,
    onSuccess: (article) => {
      client.setQueryData([...key(ws), 'articles', 'detail', article.id], article)
      staleArticles(client, ws)
    },
  })
}

export function useUpdateArticle(ws: string, id: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: async (body: Partial<ArticleInput>) => (await api.patch<Article>(`/workspaces/${ws}/knowledge/articles/${id}/`, body)).data,
    onSuccess: (article) => {
      client.setQueryData([...key(ws), 'articles', 'detail', id], article)
      staleArticles(client, ws)
    },
  })
}

/** Status endpoints return the article without its body, so the cached detail keeps the content it already has. */
export function useArticleStatus(ws: string, id: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: async (action: 'publish' | 'unpublish' | 'archive') => (await api.post<Article>(`/workspaces/${ws}/knowledge/articles/${id}/${action}/`)).data,
    onSuccess: (article) => {
      client.setQueryData<Article>([...key(ws), 'articles', 'detail', id], (current) => ({ ...article, content: current?.content }))
      staleArticles(client, ws)
    },
  })
}

export function useDeleteArticle(ws: string, id: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: () => api.delete(`/workspaces/${ws}/knowledge/articles/${id}/`),
    onSuccess: () => {
      client.removeQueries({ queryKey: [...key(ws), 'articles', 'detail', id] })
      staleArticles(client, ws)
    },
  })
}

/** Categories are only fetched when a filter or editor that shows them opens (`enabled`). */
export function useCategories(ws: string, enabled: boolean) {
  return useQuery({
    queryKey: [...key(ws), 'categories'],
    enabled,
    queryFn: async () => (await apiList<Category>(`/workspaces/${ws}/knowledge/categories/`, { limit: 100 })).items,
  })
}

export function useCategoryMutations(ws: string) {
  const client = useQueryClient()
  const edit = (change: (list: Category[]) => Category[]) =>
    client.setQueryData<Category[]>([...key(ws), 'categories'], (list) => (list ? change(list) : list))
  return {
    create: useMutation({
      mutationFn: async (name: string) => (await api.post<Category>(`/workspaces/${ws}/knowledge/categories/`, { name })).data,
      onSuccess: (category) => edit((list) => [...list, category]),
    }),
    rename: useMutation({
      mutationFn: async ({ id, name }: { id: string; name: string }) => (await api.patch<Category>(`/workspaces/${ws}/knowledge/categories/${id}/`, { name })).data,
      onSuccess: (category) => {
        edit((list) => list.map((c) => (c.id === category.id ? category : c)))
        staleArticles(client, ws)
      },
    }),
    remove: useMutation({
      mutationFn: async (id: string) => {
        await api.delete(`/workspaces/${ws}/knowledge/categories/${id}/`)
        return id
      },
      onSuccess: (id) => {
        edit((list) => list.filter((c) => c.id !== id))
        staleArticles(client, ws)
      },
    }),
  }
}

export type UploadFilters = { category?: string; filename?: string }

/** Files filed under categories (newest 100). Fetched while the Articles page shows them or the graph is open. */
export function useUploads(ws: string, filters: UploadFilters, enabled = true) {
  const query = { ...filters, limit: 100 }
  return useQuery({
    queryKey: [...key(ws), 'uploads', query],
    enabled,
    queryFn: async ({ signal }) => (await apiList<Upload>(`/workspaces/${ws}/knowledge/uploads/`, query, signal)).items,
  })
}

export function useStorage(ws: string, enabled: boolean) {
  return useQuery({
    queryKey: [...key(ws), 'storage'],
    enabled,
    queryFn: async () => (await api.get<StorageUsage>(`/workspaces/${ws}/knowledge/storage/`)).data,
  })
}

type SignedUpload = Upload & { upload_url: string; expires_in: number; headers: Record<string, string> }

/** Three steps: ask for a signed URL, PUT the bytes straight to storage, confirm. */
export function useUploadFile(ws: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: async ({ file, categoryId }: { file: File; categoryId: string }) => {
      const signed = (await api.post<SignedUpload>(`/workspaces/${ws}/knowledge/uploads/upload-url/`, { filename: file.name, content_type: file.type, size: file.size, category_id: categoryId })).data
      let response: Response
      try {
        response = await fetch(signed.upload_url, { method: 'PUT', headers: signed.headers, body: file })
      } catch {
        throw new ApiError(0, 'The file could not be sent to storage. Check your connection and try again.', 'network_error')
      }
      if (!response.ok) throw new ApiError(response.status, 'Storage rejected the file. Try again.', 'upload_failed')
      return (await api.post<Upload>(`/workspaces/${ws}/knowledge/uploads/${signed.id}/confirm/`)).data
    },
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: [...key(ws), 'uploads'] })
      void client.invalidateQueries({ queryKey: [...key(ws), 'storage'] })
    },
  })
}

export function useDeleteUpload(ws: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/workspaces/${ws}/knowledge/uploads/${id}/`)
      return id
    },
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: [...key(ws), 'uploads'] })
      void client.invalidateQueries({ queryKey: [...key(ws), 'storage'] })
    },
  })
}

/** Signed download URL, requested when the user clicks Download. */
export async function getDownloadUrl(ws: string, id: string): Promise<string> {
  return (await api.get<{ download_url: string }>(`/workspaces/${ws}/knowledge/uploads/${id}/download/`)).data.download_url
}
