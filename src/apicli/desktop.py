"""Desktop shell: serve the local API/SPA and show it in a native webview."""

from __future__ import annotations

import secrets
import socket
import threading
import time
from pathlib import Path

import uvicorn

from .server.app import create_app


def free_port() -> int:
    """Ask the OS for an unused loopback port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class DesktopApi:
    """Native file dialogs exposed to the SPA as ``window.pywebview.api``.

    The browser build falls back to anchor downloads and an ``<input type=file>``;
    inside a pywebview window those are unreliable, so export/share/import route
    through these methods instead.
    """

    @staticmethod
    def _selected_path(result: object) -> str | None:
        """Normalize a pywebview dialog result to a single path.

        macOS returns a bare string for the save dialog but a tuple for open;
        Windows/Linux return a tuple for both (or None when cancelled).
        """
        if result is None:
            return None
        if isinstance(result, str):
            return result or None
        if isinstance(result, (list, tuple)):
            return str(result[0]) if result else None
        return None

    def save_text(self, default_name: str, content: str) -> str | None:
        """Prompt for a path and write ``content`` there. Returns the path or None."""
        import webview

        if not webview.windows:
            return None
        result = webview.windows[0].create_file_dialog(
            webview.FileDialog.SAVE, save_filename=default_name
        )
        path = self._selected_path(result)
        if not path:
            return None
        target = Path(path)
        target.write_text(content, encoding="utf-8")
        return str(target)

    def open_text(self) -> dict | None:
        """Prompt for a file and return ``{"name", "content"}`` or None."""
        import webview

        if not webview.windows:
            return None
        result = webview.windows[0].create_file_dialog(
            webview.FileDialog.OPEN,
            allow_multiple=False,
            file_types=("JSON files (*.json)", "All files (*.*)"),
        )
        path = self._selected_path(result)
        if not path:
            return None
        source = Path(path)
        return {"name": source.name, "content": source.read_text(encoding="utf-8")}


def _start_server(token: str, port: int) -> uvicorn.Server:
    config = uvicorn.Config(
        create_app(token=token),
        host="127.0.0.1",
        port=port,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    threading.Thread(target=server.run, name="apicli-server", daemon=True).start()
    for _ in range(200):
        if server.started:
            break
        time.sleep(0.05)
    return server


def main() -> None:
    import webview

    token = secrets.token_urlsafe(32)
    port = free_port()
    server = _start_server(token, port)
    url = f"http://127.0.0.1:{port}/#token={token}"
    try:
        webview.create_window(
            "apicli",
            url,
            width=1280,
            height=820,
            min_size=(900, 600),
            js_api=DesktopApi(),
        )
        webview.start()
    finally:
        server.should_exit = True


if __name__ == "__main__":
    main()
