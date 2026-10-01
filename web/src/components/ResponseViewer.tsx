import { useState } from 'react'

import { CodeEditor } from './CodeEditor'
import type { ApiResponse } from '../types'

interface ResponseViewerProps {
  response: ApiResponse | null
  loading: boolean
}

type Tab = 'body' | 'headers' | 'timing'

function statusColor(response: ApiResponse): string {
  if (response.error) return 'text-danger'
  if (response.ok) return 'text-mint'
  if (response.status_code >= 400) return 'text-danger'
  return 'text-warn'
}

function looksLikeJson(body: string): boolean {
  const trimmed = body.trimStart()
  if (!(trimmed.startsWith('{') || trimmed.startsWith('['))) return false
  try {
    JSON.parse(body)
    return true
  } catch {
    return false
  }
}

export function ResponseViewer({ response, loading }: ResponseViewerProps) {
  const [tab, setTab] = useState<Tab>('body')

  const tabButton = (key: Tab, label: string) => (
    <button
      key={key}
      type="button"
      onClick={() => setTab(key)}
      className={
        'border-b-2 px-3 py-1 text-sm transition-colors ' +
        (tab === key
          ? 'border-magenta text-magenta'
          : 'border-transparent text-dim hover:text-white')
      }
    >
      {label}
    </button>
  )

  if (loading) {
    return <p className="p-4 text-sm text-neon">Sending…</p>
  }

  if (!response) {
    return <p className="p-4 text-sm text-dim">No response yet.</p>
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex items-center gap-3 px-3 pt-3">
        <span className={'text-sm font-bold ' + statusColor(response)}>
          {response.error
            ? 'ERROR'
            : `${response.status_code} ${response.reason}`.trim()}
        </span>
        {!response.error && (
          <span className="text-xs text-dim">
            {response.elapsed_ms} ms · {response.size_bytes} B
          </span>
        )}
      </div>
      {response.error && (
        <p className="px-3 pt-1 text-sm text-danger">{response.error}</p>
      )}

      <div className="mt-2 flex border-b border-edge px-2">
        {tabButton('body', 'Body')}
        {tabButton('headers', 'Headers')}
        {tabButton('timing', 'Timing')}
      </div>

      <div className="min-h-0 flex-1 overflow-hidden p-3">
        {tab === 'body' && (
          <CodeEditor
            value={response.body}
            readOnly
            language={looksLikeJson(response.body) ? 'json' : 'text'}
          />
        )}

        {tab === 'headers' && (
          <div className="h-full overflow-auto text-sm">
            {response.headers.length === 0 && (
              <p className="text-dim">No headers.</p>
            )}
            {response.headers.map(([key, val], i) => (
              <div key={i} className="flex gap-2 border-b border-edge/50 py-1">
                <span className="w-56 shrink-0 text-neon">{key}</span>
                <span className="text-white/90">{val}</span>
              </div>
            ))}
          </div>
        )}

        {tab === 'timing' && (
          <div className="h-full overflow-auto text-sm">
            {response.timeline.length === 0 && (
              <p className="text-dim">No timeline captured.</p>
            )}
            {response.timeline.map((event, i) => (
              <div key={i} className="flex justify-between border-b border-edge/50 py-1">
                <span className="text-white/90">{event.label}</span>
                <span className="text-dim">{event.elapsed_ms} ms</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
