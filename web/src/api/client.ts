import type {
  ApiResponse,
  CollectionDetail,
  CollectionSummary,
  RequestData,
  SavedRequestDetail,
} from '../types'
import { desktopApi } from './desktop'

function readToken(): string {
  // The desktop shell (pywebview) hands us a per-session token in the URL
  // fragment, which never leaves the renderer. Persist it and drop it from the
  // address bar so it isn't available to the server logs or other pages.
  const params = new URLSearchParams(window.location.hash.replace(/^#/, ''))
  const fromHash = params.get('token')
  if (fromHash) {
    localStorage.setItem('apicli-token', fromHash)
    window.history.replaceState(null, '', window.location.pathname)
    return fromHash
  }
  return localStorage.getItem('apicli-token') ?? ''
}

const TOKEN = readToken()

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    'content-type': 'application/json',
    ...(TOKEN ? { authorization: `Bearer ${TOKEN}` } : {}),
    ...((init.headers as Record<string, string>) ?? {}),
  }
  const response = await fetch(`/api${path}`, { ...init, headers })
  if (!response.ok) {
    let detail = response.statusText
    try {
      const payload = await response.json()
      detail = payload.detail ?? detail
    } catch {
      // non-JSON error body; keep statusText
    }
    throw new ApiError(response.status, detail)
  }
  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}

function filenameFrom(response: Response, fallback: string): string {
  const disposition = response.headers.get('content-disposition') ?? ''
  const match = /filename="?([^"]+)"?/.exec(disposition)
  return match ? match[1] : fallback
}

async function saveText(
  path: string,
  payload: unknown,
  fallbackName: string,
): Promise<boolean> {
  const response = await fetch(`/api${path}`, {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      ...(TOKEN ? { authorization: `Bearer ${TOKEN}` } : {}),
    },
    body: JSON.stringify(payload),
  })
  if (!response.ok) {
    throw new ApiError(response.status, response.statusText)
  }
  const text = await response.text()
  const filename = filenameFrom(response, fallbackName)

  // Desktop: use a native save dialog. Browser: download via a blob anchor.
  const api = desktopApi()
  if (api?.save_text) {
    const savedPath = await api.save_text(filename, text)
    return Boolean(savedPath)
  }
  const blob = new Blob([text], {
    type: response.headers.get('content-type') ?? 'text/plain',
  })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
  return true
}

export const apiClient = {
  listCollections: () => api<CollectionSummary[]>('/collections'),
  getCollection: (name: string) =>
    api<CollectionDetail>(`/collections/${encodeURIComponent(name)}`),
  createCollection: (name: string) =>
    api<CollectionDetail>('/collections', {
      method: 'POST',
      body: JSON.stringify({ name }),
    }),
  deleteCollection: (name: string) =>
    api<void>(`/collections/${encodeURIComponent(name)}`, { method: 'DELETE' }),
  getRequest: (collection: string, id: string) =>
    api<SavedRequestDetail>(
      `/collections/${encodeURIComponent(collection)}/requests/${id}`,
    ),
  createRequest: (collection: string, name: string, request: RequestData) =>
    api<SavedRequestDetail>(
      `/collections/${encodeURIComponent(collection)}/requests`,
      { method: 'POST', body: JSON.stringify({ name, request }) },
    ),
  updateRequest: (
    collection: string,
    id: string,
    name: string,
    request: RequestData,
  ) =>
    api<SavedRequestDetail>(
      `/collections/${encodeURIComponent(collection)}/requests/${id}`,
      { method: 'PUT', body: JSON.stringify({ name, request }) },
    ),
  deleteRequest: (collection: string, id: string) =>
    api<void>(
      `/collections/${encodeURIComponent(collection)}/requests/${id}`,
      { method: 'DELETE' },
    ),
  send: (request: RequestData) =>
    api<ApiResponse>('/send', {
      method: 'POST',
      body: JSON.stringify({ request }),
    }),
  importRequest: (raw: unknown) =>
    api<{ name: string; request: RequestData }>('/import', {
      method: 'POST',
      body: JSON.stringify(raw),
    }),
  exportExchange: (name: string, request: RequestData, response: ApiResponse) =>
    saveText('/export', { name, request, response }, `${name}.txt`),
  shareRequest: (name: string, request: RequestData) =>
    saveText('/share', { name, request }, `${name}.json`),
}
