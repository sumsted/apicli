"""Modal to name and persist the current request into a collection."""

from __future__ import annotations

from dataclasses import dataclass

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select


@dataclass
class SaveRequestResult:
    name: str
    collection_name: str
    create_new_collection: bool = False


class SaveRequestModal(ModalScreen[SaveRequestResult]):
    """Collect a request name and target collection; dismisses with the result."""

    def __init__(
        self,
        request_name: str,
        collections: list[str],
        default_collection: str | None = None,
    ) -> None:
        super().__init__()
        self._request_name = request_name
        self._collections = collections
        self._default_collection = default_collection

    def compose(self) -> ComposeResult:
        with Vertical(id="modal"):
            yield Label("Save request", classes="modal-title")
            yield Label("Name")
            yield Input(self._request_name, placeholder="request name", id="save-name")
            yield Label("Collection")
            if self._collections:
                yield Select(
                    [(name, name) for name in self._collections],
                    prompt="Create a new collection…",
                    value=Select.NULL,
                    allow_blank=True,
                    id="save-collection",
                )
            else:
                yield Label("[dim]No collections yet — a new one will be created.[/dim]")
            yield Label("New collection name (if creating)", id="new-coll-label")
            yield Input(placeholder="collection name", id="save-new-collection")
            with Horizontal():
                yield Button("Save", id="save-confirm", variant="primary")
                yield Button("Cancel", id="save-cancel")

    def on_mount(self) -> None:
        self._collection = self.query_one("#save-collection", Select) if self._collections else None
        self._new_name = self.query_one("#save-new-collection", Input)
        self._new_label = self.query_one("#new-coll-label")
        if (
            self._collection is not None
            and self._default_collection in self._collections
        ):
            self._collection.value = self._default_collection
        blank = self._collection is None or (
            self._collection.value is None or self._collection.value is Select.NULL
        )
        self._new_name.display = blank
        self._new_label.display = blank

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "save-collection":
            blank = event.value is None or event.value is Select.NULL
            self._new_name.display = blank
            self._new_label.display = blank

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-confirm":
            self._confirm()
        elif event.button.id == "save-cancel":
            self.dismiss(None)

    def _confirm(self) -> None:
        name = self.query_one("#save-name", Input).value.strip()
        if not name:
            self.notify("Request name is required.", severity="error")
            return
        create_new = False
        collection_name = ""
        if self._collection is not None:
            value = self._collection.value
            if value is not None and value is not Select.NULL and value != "__none__":
                collection_name = str(value)
            else:
                create_new = True
        else:
            create_new = True
        if create_new:
            collection_name = self._new_name.value.strip()
            if not collection_name:
                self.notify("Collection name is required.", severity="error")
                return
        self.dismiss(
            SaveRequestResult(
                name=name,
                collection_name=collection_name,
                create_new_collection=create_new,
            )
        )