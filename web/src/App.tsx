import { useCallback, useEffect, useRef, useState } from 'react'

import { ApiError, apiClient } from './api/client'
import { desktopApi } from './api/desktop'
import { CollectionsPanel } from './components/CollectionsPanel'
import { RequestEditor } from './components/RequestEditor'
import { ResponseViewer } from './components/ResponseViewer'
import { SaveDialog } from './components/SaveDialog'
import { defaultRequest, type ApiResponse, type CollectionSummary, type RequestData } from './types'

type SaveMode = 'save' | 'clone'

export default function App() {
  const [request, setRequest] = useState<RequestData>(defaultRequest)
  const [response, setResponse] = useState<ApiResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [collections, setCollections] = useState<CollectionSummary[]>([])
  const [currentCollection, setCurrentCollection] = useState<string | null>(null)
  const [currentSaved, setCurrentSaved] = useState<{ id: string; name: string } | null>(
    null,
  )
  const [saveMode, setSaveMode] = useState<SaveMode | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const refreshCollections = useCallback(async () => {
    try {
      setCollections(await apiClient.listCollections())
    } catch (err) {
      setMessage(err instanceof Error ? err.message : String(err))
    }
  }, [])

  useEffect(() => {
    void refreshCollections()
  }, [refreshCollections])

  const notify = (text: string) => setMessage(text)

  const handleSend = useCallback(async () => {
    if (!request.url.trim()) {
      notify('Enter a URL first.')
      return
    }
    setLoading(true)
    setResponse(null)
    try {
      setResponse(await apiClient.send(request))
    } catch (err) {
      notify(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }, [request])

  const openSaveDialog = (mode: SaveMode) => {
    setMessage(null)
    setSaveMode(mode)
  }

  const handleSave = () => {
    if (currentSaved && currentCollection) {
      void apiClient
        .updateRequest(currentCollection, currentSaved.id, currentSaved.name, request)
        .then(() => notify(`Saved '${currentSaved.name}'`))
        .catch((err) => notify(String(err)))
      return
    }
    openSaveDialog('save')
  }

  const handleSaveConfirm = async (
    name: string,
    collection: string,
    createNew: boolean,
  ) => {
    setSaveMode(null)
    try {
      if (createNew) {
        try {
          await apiClient.createCollection(collection)
        } catch (err) {
          if (!(err instanceof ApiError && err.status === 409)) throw err
        }
      }
      const saved = await apiClient.createRequest(collection, name, request)
      setCurrentSaved({ id: saved.id, name: saved.name })
      setCurrentCollection(collection)
      notify(`${saveMode === 'clone' ? 'Cloned' : 'Saved'} '${saved.name}' into '${collection}'`)
      await refreshCollections()
    } catch (err) {
      notify(err instanceof Error ? err.message : String(err))
    }
  }

  const handleLoad = async (collection: string, id: string) => {
    try {
      const saved = await apiClient.getRequest(collection, id)
      setRequest(saved.request)
      setCurrentSaved({ id: saved.id, name: saved.name })
      setCurrentCollection(collection)
      setResponse(null)
      notify(`Loaded '${saved.name}'`)
    } catch (err) {
      notify(err instanceof Error ? err.message : String(err))
    }
  }

  const handleNewRequest = () => {
    setRequest(defaultRequest())
    setCurrentSaved(null)
    setCurrentCollection(null)
    setResponse(null)
    notify('New request')
  }

  const requestName = () => {
    if (currentSaved) return currentSaved.name
    const derived = `${request.method} ${request.url}`.trim()
    return derived || 'Untitled request'
  }

  const handleExport = async () => {
    if (!response) {
      notify('No response to export yet.')
      return
    }
    try {
      const saved = await apiClient.exportExchange(requestName(), request, response)
      notify(saved ? 'Exported exchange' : 'Export cancelled')
    } catch (err) {
      notify(err instanceof Error ? err.message : String(err))
    }
  }

  const handleShare = async () => {
    if (!request.url.trim()) {
      notify('Nothing to share — enter a URL first.')
      return
    }
    try {
      const saved = await apiClient.shareRequest(requestName(), request)
      notify(saved ? 'Shared request' : 'Share cancelled')
    } catch (err) {
      notify(err instanceof Error ? err.message : String(err))
    }
  }

  const doImport = async (raw: unknown) => {
    try {
      const imported = await apiClient.importRequest(raw)
      setRequest(imported.request)
      setCurrentSaved(null)
      setCurrentCollection(null)
      setResponse(null)
      notify(`Imported '${imported.name}'`)
    } catch (err) {
      notify(err instanceof Error ? err.message : String(err))
    }
  }

  const handleImportClick = async () => {
    const api = desktopApi()
    if (api?.open_text) {
      const picked = await api.open_text()
      if (!picked) return
      try {
        await doImport(JSON.parse(picked.content))
      } catch {
        notify('That file is not valid JSON.')
      }
      return
    }
    fileInputRef.current?.click()
  }

  const handleImportFile = async (file: File) => {
    try {
      await doImport(JSON.parse(await file.text()))
    } catch {
      notify('That file is not valid JSON.')
    }
  }

  const handleNewCollection = async () => {
    const name = window.prompt('New collection name')
    if (!name?.trim()) return
    try {
      await apiClient.createCollection(name.trim())
      await refreshCollections()
      notify(`Created collection '${name.trim()}'`)
    } catch (err) {
      notify(err instanceof Error ? err.message : String(err))
    }
  }

  const handleDeleteRequest = async (collection: string, id: string) => {
    try {
      await apiClient.deleteRequest(collection, id)
      if (currentSaved?.id === id && currentCollection === collection) {
        setCurrentSaved(null)
        setCurrentCollection(null)
      }
      await refreshCollections()
      notify('Request deleted')
    } catch (err) {
      notify(err instanceof Error ? err.message : String(err))
    }
  }

  const handleDeleteCollection = async (collection: string) => {
    if (!window.confirm(`Delete collection '${collection}'?`)) return
    try {
      await apiClient.deleteCollection(collection)
      if (currentCollection === collection) {
        setCurrentSaved(null)
        setCurrentCollection(null)
      }
      await refreshCollections()
      notify(`Deleted '${collection}'`)
    } catch (err) {
      notify(err instanceof Error ? err.message : String(err))
    }
  }

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const mod = event.metaKey || event.ctrlKey
      if (mod && event.key === 'Enter') {
        event.preventDefault()
        void handleSend()
      } else if (mod && event.shiftKey && event.key.toLowerCase() === 's') {
        event.preventDefault()
        openSaveDialog('clone')
      } else if (mod && event.key.toLowerCase() === 's') {
        event.preventDefault()
        handleSave()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  const defaultSaveName = currentSaved
    ? `${currentSaved.name} copy`
    : `${request.method} ${request.url}`.trim() || 'Untitled request'

  const actionClass =
    'rounded border border-edge px-3 py-1 text-sm hover:bg-panel-2'

  return (
    <div className="flex h-full flex-col">
      <input
        ref={fileInputRef}
        type="file"
        accept="application/json,.json"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) void handleImportFile(file)
          e.target.value = ''
        }}
      />
      <header className="flex items-center gap-2 border-b border-edge px-3 py-2">
        <span className="mr-2 font-bold text-neon">apicli</span>
        <button
          type="button"
          onClick={() => openSaveDialog('save')}
          className={actionClass + ' text-white'}
        >
          Save
        </button>
        <button
          type="button"
          onClick={() => openSaveDialog('clone')}
          className={actionClass + ' text-white'}
        >
          Clone
        </button>
        <button
          type="button"
          onClick={handleNewRequest}
          className={actionClass + ' text-white'}
        >
          New
        </button>
        <button
          type="button"
          onClick={() => void handleImportClick()}
          className={actionClass + ' text-white'}
        >
          Import
        </button>
        <button
          type="button"
          onClick={() => void handleShare()}
          className={actionClass + ' text-white'}
        >
          Share
        </button>
        <button
          type="button"
          onClick={() => void handleExport()}
          disabled={!response}
          className={actionClass + ' text-white disabled:opacity-40'}
        >
          Export
        </button>
        <button
          type="button"
          onClick={() => void handleSend()}
          className="rounded border border-neon px-3 py-1 text-sm font-bold text-neon hover:bg-panel-2"
        >
          Send
        </button>
        <span className="ml-auto truncate text-xs text-dim">
          {message ?? (currentSaved ? currentSaved.name : 'unsaved request')}
        </span>
      </header>

      <div className="flex min-h-0 flex-1">
        <aside className="w-64 border-r border-edge bg-panel">
          <CollectionsPanel
            collections={collections}
            activeCollection={currentCollection}
            activeRequestId={currentSaved?.id ?? null}
            onLoad={handleLoad}
            onNewCollection={handleNewCollection}
            onDeleteCollection={handleDeleteCollection}
            onDeleteRequest={handleDeleteRequest}
          />
        </aside>

        <main className="flex min-h-0 flex-1">
          <section className="flex min-h-0 w-1/2 flex-col border-r border-edge">
            <RequestEditor value={request} onChange={setRequest} />
          </section>
          <section className="flex min-h-0 w-1/2 flex-col">
            <ResponseViewer response={response} loading={loading} />
          </section>
        </main>
      </div>

      {saveMode && (
        <SaveDialog
          title={saveMode === 'clone' ? 'Clone request' : 'Save request'}
          defaultName={defaultSaveName}
          defaultCollection={currentCollection}
          collections={collections}
          onCancel={() => setSaveMode(null)}
          onConfirm={(name, collection, createNew) =>
            void handleSaveConfirm(name, collection, createNew)
          }
        />
      )}
    </div>
  )
}
