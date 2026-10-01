# apicli

A Postman/Bruno-style API testing TUI built with Python and [Textual](https://textual.textualize.io/).

Two-pane layout: compose and send requests on the left, read responses on the right — no mouse required.

## Features

- **Request editor** with method + URL, and tabbed Body / Headers / Auth sections
- **Body types** `json`, `text`, and `xml` with tree-sitter syntax highlighting
- **Authentication**: Basic and OAuth2 client-credentials flows
- **Response viewer** with status/elapsed/size, colorized body, headers, and timing tabs
- Select and copy response bodies (`ctrl+a` / `ctrl+c`)
- **Collections** managed in a `ctrl+p` popup with JSON storage on disk
- **Clone** a loaded request into a new one via the save dialog (`ctrl+shift+s`)
- **Export** the full exchange (request, response, timeline) as a readable report
- **Share / Import** requests as JSON for portability between machines
- **Optional cyberpunk theme** via `APICLI_THEME=cyberpunk` or toggle with `ctrl+t`

## Install

Requires Python 3.12+.

```sh
pip install -e '/path/to/apicli[test]'
```

Runs on top of Textual >= 8.2 and httpx >= 0.28.

## Usage

```sh
apicli
```

### Keybindings

| Key            | Action             |
|----------------|--------------------|
| `ctrl+r`       | Send request       |
| `ctrl+s`       | Save request       |
| `ctrl+shift+s` | Clone request      |
| `ctrl+p`       | Open collections   |
| `ctrl+n`       | New request        |
| `ctrl+o`       | New collection     |
| `ctrl+d`       | Delete request     |
| `ctrl+e`       | Export exchange    |
| `ctrl+shift+e` | Share request      |
| `ctrl+i`       | Import request     |
| `ctrl+t`       | Toggle cyberpunk theme |

In the request/response editors, `ctrl+a` selects all and `ctrl+c` copies.

### Themes

Two schemes ship with apicli: the default `textual-dark` and a neon
**cyberpunk** theme. Start in cyberpunk with `APICLI_THEME=cyberpunk apicli`, or
press `ctrl+t` at runtime to toggle between the two.

## Data & storage

The data location is resolved in order of priority:

1. `$APICLI_DATA_DIR` if set (absolute or `~` paths honored);
2. `./data` when you launch `apicli` inside a project directory (a folder
   containing `pyproject.toml` or `.git`);
3. `~/apicli/data` as the default for a globally installed `apicli` run from
   anywhere else.

- Collections (request JSON) live in the resolved data directory.
- Exported exchange reports are written to `{data_dir}/exports/` as
  `{slug}-{YYYYMMDD-HHMMSS}.txt`, and shared requests as `.json` files.
- Response bodies are pretty-printed JSON, matching the request editor.

## Development

```sh
python -m pytest -q
```

The test suite drives the TUI headlessly with Textual's test runner.

## Web interface (in progress)

A local FastAPI backend exposes the same core (collections, requests, send) for
a browser and future desktop (pywebview) UI. The SPA mirrors the TUI: send,
collections CRUD, save/clone, import/export/share, and Basic/OAuth2 auth with
the TLS toggle.

```sh
# Terminal 1 — backend
pip install -e '.[web]'
apicli-web              # http://127.0.0.1:8000

# Terminal 2 — SPA with hot reload (proxies /api to the backend)
cd web
npm install
npm run dev             # http://127.0.0.1:5173
```

For a production bundle, `npm run build` writes `web/dist`, which `apicli-web`
serves at `/` alongside the API. Interactive API docs are at `/docs`. The
server imports only the UI-agnostic core (`models`, `storage`, `client`,
`auth`, `export`, `share`) — no Textual — so it stays small enough to bundle
into a desktop app later.

### Desktop app (pywebview)

The same SPA runs as a native desktop window. The shell starts the FastAPI
server on a random loopback port with a per-session bearer token, then opens a
pywebview window pointed at it (the token is passed in the URL fragment, so it
never hits the server or disk).

```sh
pip install -e '.[desktop]'
npm --prefix web run build      # produce web/dist first
apicli-desktop
```

On macOS this uses WKWebView (via pyobjc), on Windows WebView2, and on Linux
WebKitGTK. Export/share/import use native save/open dialogs through the
pywebview bridge; in a plain browser they fall back to regular downloads and
the file picker.

### Packaging the desktop app

PyInstaller bundles the Python core, the FastAPI server, pywebview, and the
prebuilt SPA into one app; Textual and the tree-sitter stack are excluded.

```sh
packaging/build_macos.sh            # dist/apicli.app (+ dist/apicli.dmg if hdiutil)
powershell packaging/build_windows.ps1   # dist/apicli/apicli.exe
packaging/build_linux.sh            # dist/apicli/apicli (needs WebKitGTK)
```

The spec lives at `packaging/apicli.spec`; it fails fast if `web/dist` is
missing, so run `npm --prefix web run build` first (the scripts do this for
you). Regenerate the macOS icon with `packaging/make_icons_macos.sh`. Bundles
are unsigned — on first macOS launch, right-click the app and choose **Open**.

## License

Apache License 2.0. See [LICENSE](LICENSE).