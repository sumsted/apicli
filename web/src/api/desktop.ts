// Bridge to the pywebview desktop shell. `window.pywebview.api` only exists
// when the SPA is running inside the native window; in a browser these helpers
// report no support and callers fall back to browser file APIs.

export interface PywebviewApi {
  save_text?: (name: string, content: string) => Promise<string | null>
  open_text?: () => Promise<{ name: string; content: string } | null>
}

export function desktopApi(): PywebviewApi | undefined {
  const holder = window as unknown as { pywebview?: { api?: PywebviewApi } }
  return holder.pywebview?.api
}
