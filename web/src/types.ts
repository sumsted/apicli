export type Header = [string, string]

export type HttpMethod =
  | 'GET'
  | 'POST'
  | 'PUT'
  | 'PATCH'
  | 'DELETE'
  | 'HEAD'
  | 'OPTIONS'

export type BodyType = 'json' | 'xml' | 'form' | 'text'

export type AuthType = 'none' | 'basic' | 'oauth2'

export interface BasicAuthConfig {
  username: string
  password: string
}

export interface OAuth2Config {
  token_url: string
  client_id: string
  client_secret: string
  scope: string
  include_client_credentials_in_body: boolean
  token_type: string
}

export interface AuthConfig {
  type: AuthType
  basic: BasicAuthConfig
  oauth2: OAuth2Config
}

export interface RequestData {
  method: HttpMethod
  url: string
  headers: Header[]
  body_type: BodyType
  body: string
  verify_tls: boolean
  auth: AuthConfig
}

export interface TimelineEvent {
  label: string
  elapsed_ms: number
}

export interface ApiResponse {
  status_code: number
  reason: string
  http_version: string
  headers: Header[]
  body: string
  elapsed_ms: number
  size_bytes: number
  ok: boolean
  url: string
  request_method: string
  error: string
  timeline: TimelineEvent[]
  sent_headers: Header[]
  sent_body: string | null
}

export interface CollectionSummary {
  name: string
  request_count: number
}

export interface RequestSummary {
  id: string
  name: string
}

export interface CollectionDetail {
  name: string
  requests: RequestSummary[]
}

export interface SavedRequestDetail {
  id: string
  name: string
  request: RequestData
}

export const HTTP_METHODS: HttpMethod[] = [
  'GET',
  'POST',
  'PUT',
  'PATCH',
  'DELETE',
  'HEAD',
  'OPTIONS',
]

export const BODY_TYPES: BodyType[] = ['json', 'xml', 'form', 'text']

export function defaultRequest(): RequestData {
  return {
    method: 'GET',
    url: '',
    headers: [],
    body_type: 'json',
    body: '',
    verify_tls: true,
    auth: {
      type: 'none',
      basic: { username: '', password: '' },
      oauth2: {
        token_url: '',
        client_id: '',
        client_secret: '',
        scope: '',
        include_client_credentials_in_body: true,
        token_type: 'Bearer',
      },
    },
  }
}
