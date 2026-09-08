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
- **Export** the full exchange (request, response, timeline) as a readable report
- **Share / Import** requests as JSON for portability between machines

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
| `ctrl+p`       | Open collections   |
| `ctrl+n`       | New request        |
| `ctrl+o`       | New collection     |
| `ctrl+d`       | Delete request     |
| `ctrl+e`       | Export exchange    |
| `ctrl+shift+e` | Share request      |
| `ctrl+i`       | Import request     |

In the request/response editors, `ctrl+a` selects all and `ctrl+c` copies.

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

## License

Apache License 2.0. See [LICENSE](LICENSE).