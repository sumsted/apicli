"""Modal to import a shared request definition."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label

from .. import storage
from ..models import RequestData
from ..share import load_request_json


class ImportRequestModal(ModalScreen[tuple[str, RequestData] | None]):
    """Dismisses with ``(name, request)`` of the imported definition."""

    def compose(self) -> ComposeResult:
        with Vertical(id="modal"):
            yield Label("Import shared request", classes="modal-title")
            yield Label("Path to a shared request .json")
            yield Input(
                value=self._default_path(),
                placeholder="/path/to/shared.json",
                id="import-path",
            )
            with Horizontal():
                yield Button("Import", id="import-confirm", variant="primary")
                yield Button("Cancel", id="import-cancel")

    def _default_path(self) -> str:
        exports = Path(storage.data_dir()) / "exports"
        if exports.is_dir():
            candidates = sorted(exports.glob("*.json"))
            if candidates:
                return str(candidates[-1])
        return ""

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "import-confirm":
            path = self.query_one("#import-path", Input).value.strip()
            if not path:
                self.notify("Enter a path to the shared file.", severity="error")
                return
            try:
                result = load_request_json(path)
            except (OSError, ValueError) as exc:
                self.notify(f"Import failed: {exc}", severity="error")
                return
            self.dismiss(result)
        elif event.button.id == "import-cancel":
            self.dismiss(None)