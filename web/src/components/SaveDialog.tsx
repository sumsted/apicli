import { useState } from 'react'

import type { CollectionSummary } from '../types'

const NEW_COLLECTION = '__new__'

interface SaveDialogProps {
  title: string
  defaultName: string
  defaultCollection: string | null
  collections: CollectionSummary[]
  onCancel: () => void
  onConfirm: (name: string, collection: string, createNew: boolean) => void
}

const inputClass =
  'w-full rounded border border-edge bg-panel px-2 py-1 text-sm text-white outline-none focus:border-neon'
const labelClass = 'mb-1 block text-xs uppercase tracking-wide text-dim'

export function SaveDialog({
  title,
  defaultName,
  defaultCollection,
  collections,
  onCancel,
  onConfirm,
}: SaveDialogProps) {
  const [name, setName] = useState(defaultName)
  const [collection, setCollection] = useState(
    defaultCollection && collections.some((c) => c.name === defaultCollection)
      ? defaultCollection
      : NEW_COLLECTION,
  )
  const [newCollection, setNewCollection] = useState('')
  const [error, setError] = useState<string | null>(null)

  const createNew = collections.length === 0 || collection === NEW_COLLECTION

  const submit = () => {
    if (!name.trim()) {
      setError('Request name is required.')
      return
    }
    if (createNew && !newCollection.trim()) {
      setError('Collection name is required.')
      return
    }
    onConfirm(
      name.trim(),
      createNew ? newCollection.trim() : collection,
      createNew,
    )
  }

  return (
    <div className="fixed inset-0 z-10 flex items-center justify-center bg-black/60">
      <div className="w-96 rounded-lg border border-edge bg-panel-2 p-4 shadow-xl">
        <h2 className="mb-3 text-sm font-bold text-neon">{title}</h2>

        <div className="mb-3">
          <label className={labelClass}>Name</label>
          <input
            className={inputClass}
            value={name}
            autoFocus
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') submit()
              if (e.key === 'Escape') onCancel()
            }}
          />
        </div>

        <div className="mb-3">
          <label className={labelClass}>Collection</label>
          {collections.length > 0 ? (
            <select
              className={inputClass}
              value={collection}
              onChange={(e) => setCollection(e.target.value)}
            >
              <option value={NEW_COLLECTION}>Create a new collection…</option>
              {collections.map((c) => (
                <option key={c.name} value={c.name}>
                  {c.name}
                </option>
              ))}
            </select>
          ) : (
            <p className="text-xs text-dim">
              No collections yet — a new one will be created.
            </p>
          )}
        </div>

        {createNew && (
          <div className="mb-3">
            <label className={labelClass}>New collection name</label>
            <input
              className={inputClass}
              value={newCollection}
              onChange={(e) => setNewCollection(e.target.value)}
            />
          </div>
        )}

        {error && <p className="mb-2 text-xs text-danger">{error}</p>}

        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded border border-edge px-3 py-1 text-sm text-dim hover:bg-panel"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={submit}
            className="rounded bg-neon px-3 py-1 text-sm font-bold text-ink hover:opacity-90"
          >
            Save
          </button>
        </div>
      </div>
    </div>
  )
}
