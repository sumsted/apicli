import { useState } from 'react'

import { CodeEditor, type EditorLanguage } from './CodeEditor'
import {
  BODY_TYPES,
  HTTP_METHODS,
  type AuthType,
  type BodyType,
  type Header,
  type RequestData,
} from '../types'

interface RequestEditorProps {
  value: RequestData
  onChange: (request: RequestData) => void
}

type Tab = 'body' | 'headers' | 'auth'

const inputClass =
  'w-full rounded border border-edge bg-panel px-2 py-1 text-sm text-white outline-none focus:border-neon'
const labelClass = 'mb-1 block text-xs uppercase tracking-wide text-dim'

const BODY_LANGUAGE: Record<BodyType, EditorLanguage> = {
  json: 'json',
  xml: 'xml',
  form: 'text',
  text: 'text',
}

export function RequestEditor({ value, onChange }: RequestEditorProps) {
  const [tab, setTab] = useState<Tab>('body')

  const patch = (partial: Partial<RequestData>) =>
    onChange({ ...value, ...partial })

  const updateHeader = (index: number, header: Header) => {
    const headers = value.headers.map((h, i) => (i === index ? header : h))
    patch({ headers })
  }

  const addHeader = () => patch({ headers: [...value.headers, ['', '']] })

  const removeHeader = (index: number) =>
    patch({ headers: value.headers.filter((_, i) => i !== index) })

  const setAuthType = (type: AuthType) =>
    patch({ auth: { ...value.auth, type } })

  const patchBasic = (partial: Partial<RequestData['auth']['basic']>) =>
    patch({ auth: { ...value.auth, basic: { ...value.auth.basic, ...partial } } })

  const patchOAuth = (partial: Partial<RequestData['auth']['oauth2']>) =>
    patch({
      auth: { ...value.auth, oauth2: { ...value.auth.oauth2, ...partial } },
    })

  const tabButton = (key: Tab, label: string) => (
    <button
      key={key}
      type="button"
      onClick={() => setTab(key)}
      className={
        'border-b-2 px-3 py-1 text-sm transition-colors ' +
        (tab === key
          ? 'border-neon text-neon'
          : 'border-transparent text-dim hover:text-white')
      }
    >
      {label}
    </button>
  )

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2 p-3">
      <div className="flex gap-2">
        <select
          className={inputClass + ' w-28'}
          value={value.method}
          onChange={(e) =>
            patch({ method: e.target.value as RequestData['method'] })
          }
        >
          {HTTP_METHODS.map((method) => (
            <option key={method} value={method}>
              {method}
            </option>
          ))}
        </select>
        <input
          className={inputClass + ' flex-1'}
          placeholder="https://api.example.com/path"
          value={value.url}
          onChange={(e) => patch({ url: e.target.value })}
        />
      </div>

      <div className="flex border-b border-edge">
        {tabButton('body', 'Body')}
        {tabButton('headers', 'Headers')}
        {tabButton('auth', 'Auth')}
      </div>

      {tab === 'body' && (
        <div className="flex min-h-0 flex-1 flex-col gap-2">
          <div className="flex items-center gap-2">
            <label className={labelClass + ' mb-0'}>Type</label>
            <select
              className={inputClass + ' w-28'}
              value={value.body_type}
              onChange={(e) => patch({ body_type: e.target.value as BodyType })}
            >
              {BODY_TYPES.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </div>
          <div className="min-h-0 flex-1 overflow-hidden rounded border border-edge bg-panel">
            <CodeEditor
              value={value.body}
              onChange={(body) => patch({ body })}
              language={BODY_LANGUAGE[value.body_type]}
              placeholderText="Request body…"
            />
          </div>
        </div>
      )}

      {tab === 'headers' && (
        <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-auto">
          {value.headers.length === 0 && (
            <p className="text-sm text-dim">No headers.</p>
          )}
          {value.headers.map((header, index) => (
            <div key={index} className="flex gap-2">
              <input
                className={inputClass}
                placeholder="Header"
                value={header[0]}
                onChange={(e) => updateHeader(index, [e.target.value, header[1]])}
              />
              <input
                className={inputClass}
                placeholder="Value"
                value={header[1]}
                onChange={(e) => updateHeader(index, [header[0], e.target.value])}
              />
              <button
                type="button"
                onClick={() => removeHeader(index)}
                className="rounded border border-edge px-2 text-danger hover:bg-panel-2"
              >
                ×
              </button>
            </div>
          ))}
          <button
            type="button"
            onClick={addHeader}
            className="self-start rounded border border-edge px-3 py-1 text-sm text-neon hover:bg-panel-2"
          >
            + Add header
          </button>
        </div>
      )}

      {tab === 'auth' && (
        <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-auto">
          <div>
            <label className={labelClass}>Auth type</label>
            <select
              className={inputClass + ' w-48'}
              value={value.auth.type}
              onChange={(e) => setAuthType(e.target.value as AuthType)}
            >
              <option value="none">None</option>
              <option value="basic">Basic</option>
              <option value="oauth2">OAuth2 client-credentials</option>
            </select>
          </div>

          {value.auth.type === 'basic' && (
            <>
              <div>
                <label className={labelClass}>Username</label>
                <input
                  className={inputClass}
                  value={value.auth.basic.username}
                  onChange={(e) => patchBasic({ username: e.target.value })}
                />
              </div>
              <div>
                <label className={labelClass}>Password</label>
                <input
                  className={inputClass}
                  type="password"
                  value={value.auth.basic.password}
                  onChange={(e) => patchBasic({ password: e.target.value })}
                />
              </div>
            </>
          )}

          {value.auth.type === 'oauth2' && (
            <>
              {(
                [
                  ['token_url', 'Token URL'],
                  ['client_id', 'Client ID'],
                  ['client_secret', 'Client secret'],
                  ['scope', 'Scope'],
                ] as const
              ).map(([field, label]) => (
                <div key={field}>
                  <label className={labelClass}>{label}</label>
                  <input
                    className={inputClass}
                    type={field === 'client_secret' ? 'password' : 'text'}
                    value={value.auth.oauth2[field]}
                    onChange={(e) => patchOAuth({ [field]: e.target.value })}
                  />
                </div>
              ))}
              <label className="flex items-center gap-2 text-sm text-dim">
                <input
                  type="checkbox"
                  checked={value.auth.oauth2.include_client_credentials_in_body}
                  onChange={(e) =>
                    patchOAuth({
                      include_client_credentials_in_body: e.target.checked,
                    })
                  }
                />
                Send client credentials in request body
              </label>
            </>
          )}

          <label className="flex items-center gap-2 text-sm text-dim">
            <input
              type="checkbox"
              checked={!value.verify_tls}
              onChange={(e) => patch({ verify_tls: !e.target.checked })}
            />
            Skip TLS certificate verification
          </label>
        </div>
      )}
    </div>
  )
}
