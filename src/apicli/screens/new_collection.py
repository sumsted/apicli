"""Modal to create a new collection."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label


class NewCollectionModal(ModalScreen[str]):
    """Dismisses with the new collection name."""

    def compose(self) -> ComposeResult:
        with Vertical(id="modal"):
            yield Label("New collection", classes="modal-title")
            yield Input(placeholder="Collection name", id="new-coll-name")
            with Horizontal():
                yield Button("Create", id="create-coll", variant="primary")
                yield Button("Cancel", id="cancel-coll")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "create-coll":
            name = self.query_one("#new-coll-name", Input).value.strip()
            if not name:
                self.notify("Collection name is required.", severity="error")
                return
            self.dismiss(name)
        elif event.button.id == "cancel-coll":
            self.dismiss(None)