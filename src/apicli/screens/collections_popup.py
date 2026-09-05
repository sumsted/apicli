"""Modal popup showing the collections tree, opened with ctrl+p."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button

from ..models import Collection
from ..widgets.collection_tree import CollectionTree

NEW_COLLECTION = "__new_collection__"


class CollectionsPopup(ModalScreen[tuple[str, str] | str | None]):
    """Dismisses with a ``(collection_name, request_id)`` tuple, the
    string ``NEW_COLLECTION``, or ``None`` when simply closed."""

    BINDINGS = [Binding("escape", "close_popup", "Close", show=False)]

    def action_close_popup(self) -> None:
        self.dismiss(None)

    def __init__(self, collections: list[Collection]) -> None:
        self._collections = collections
        super().__init__()

    def compose(self) -> ComposeResult:
        with Vertical(id="collections-popup", classes="collections-modal"):
            yield CollectionTree(id="collections")
            with Horizontal(id="popup-actions"):
                yield Button("New collection", id="popup-new-collection")
                yield Button("Close", id="popup-close", variant="default")

    def on_mount(self) -> None:
        self.border_title = "Collections"
        self.query_one("#collections", CollectionTree).apply_data(self._collections)

    def on_collection_tree_request_selected(
        self, event: CollectionTree.RequestSelected
    ) -> None:
        self.dismiss((event.collection_name, event.request_id))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "popup-new-collection":
            self.dismiss(NEW_COLLECTION)
        elif event.button.id == "popup-close":
            self.dismiss(None)