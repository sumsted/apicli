import { useState } from 'react'

import { apiClient } from '../api/client'
import type { CollectionSummary, RequestSummary } from '../types'

interface CollectionsPanelProps {
  collections: CollectionSummary[]
  activeCollection: string | null
  activeRequestId: string | null
  onLoad: (collection: string, id: string) => void
  onNewCollection: () => void
  onDeleteCollection: (collection: string) => void
  onDeleteRequest: (collection: string, id: string) => void
}

export function CollectionsPanel({
  collections,
  activeCollection,
  activeRequestId,
  onLoad,
  onNewCollection,
  onDeleteCollection,
  onDeleteRequest,
}: CollectionsPanelProps) {
  const [expanded, setExpanded] = useState<string | null>(null)
  const [requests, setRequests] = useState<Record<string, RequestSummary[]>>({})
  const [error, setError] = useState<string | null>(null)

  const toggle = async (name: string) => {
    if (expanded === name) {
      setExpanded(null)
      return
    }
    setExpanded(name)
    setError(null)
    try {
      const detail = await apiClient.getCollection(name)
      setRequests((prev) => ({ ...prev, [name]: detail.requests }))
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  const refreshDetail = async (name: string) => {
    try {
      const detail = await apiClient.getCollection(name)
      setRequests((prev) => ({ ...prev, [name]: detail.requests }))
    } catch {
      setRequests((prev) => ({ ...prev, [name]: [] }))
    }
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center justify-between border-b border-edge px-3 py-2">
        <span className="text-xs uppercase tracking-wide text-dim">
          Collections
        </span>
        <button
          type="button"
          onClick={onNewCollection}
          className="rounded border border-edge px-2 py-0.5 text-xs text-neon hover:bg-panel-2"
        >
          + New
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-auto p-2 text-sm">
        {error && <p className="mb-2 text-xs text-danger">{error}</p>}
        {collections.length === 0 && (
          <p className="text-dim">No collections yet.</p>
        )}
        {collections.map((collection) => (
          <div key={collection.name} className="mb-1">
            <div className="group flex items-center gap-1">
              <button
                type="button"
                onClick={() => toggle(collection.name)}
                className="flex-1 truncate rounded px-2 py-1 text-left text-white hover:bg-panel-2"
              >
                <span className="mr-1 text-dim">
                  {expanded === collection.name ? '▾' : '▸'}
                </span>
                {collection.name}
                <span className="ml-1 text-xs text-dim">
                  ({collection.request_count})
                </span>
              </button>
              <button
                type="button"
                title="Delete collection"
                onClick={() => {
                  onDeleteCollection(collection.name)
                  if (expanded === collection.name) setExpanded(null)
                }}
                className="hidden px-1 text-xs text-danger group-hover:block"
              >
                ✕
              </button>
            </div>

            {expanded === collection.name && (
              <div className="ml-3 border-l border-edge pl-2">
                {(requests[collection.name] ?? []).length === 0 && (
                  <p className="px-2 py-1 text-xs text-dim">No requests.</p>
                )}
                {(requests[collection.name] ?? []).map((req) => {
                  const active =
                    collection.name === activeCollection &&
                    req.id === activeRequestId
                  return (
                    <div key={req.id} className="group flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => onLoad(collection.name, req.id)}
                        className={
                          'flex-1 truncate rounded px-2 py-1 text-left hover:bg-panel-2 ' +
                          (active ? 'text-neon' : 'text-white/90')
                        }
                      >
                        {req.name}
                      </button>
                      <button
                        type="button"
                        title="Delete request"
                        onClick={async () => {
                          onDeleteRequest(collection.name, req.id)
                          await refreshDetail(collection.name)
                        }}
                        className="hidden px-1 text-xs text-danger group-hover:block"
                      >
                        ✕
                      </button>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
