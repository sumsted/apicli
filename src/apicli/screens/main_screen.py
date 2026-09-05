"""The main three-pane workspace screen."""

from __future__ import annotations

from copy import deepcopy

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Header, Footer

from .. import storage
from ..client import send_request
from ..export import export_exchange
from ..models import Collection, RequestData, ResponseData, SavedRequest
from ..share import export_request_json
from ..widgets.request_editor import RequestEditor
from ..widgets.response_viewer import ResponseViewer
from .collections_popup import CollectionsPopup, NEW_COLLECTION
from .import_request import ImportRequestModal
from .new_collection import NewCollectionModal
from .save_request import SaveRequestModal


class MainScreen(Screen):
    BINDINGS = [
        Binding("ctrl+r", "send", "Send", priority=True),
        Binding("ctrl+s", "save_request", "Save", priority=True),
        Binding("ctrl+e", "export_response", "Export", priority=True),
        Binding("ctrl+shift+e", "share_request", "Share req", priority=True),
        Binding("ctrl+i", "import_request", "Import", priority=True),
        Binding("ctrl+p", "open_collections", "Collections", priority=True),
        Binding("ctrl+n", "new_request", "New request", priority=True),
        Binding("ctrl+o", "new_collection", "New collection", priority=True),
        Binding("ctrl+d", "delete_request", "Delete", priority=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.collections: list[Collection] = []
        self.current_request = RequestData()
        self.current_saved: SavedRequest | None = None
        self.current_collection: Collection | None = None
        self.last_request: RequestData | None = None
        self.last_response: ResponseData | None = None
        self.data_dir = storage.data_dir()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="workspace"):
            yield RequestEditor(id="editor")
            yield ResponseViewer(id="response")
        yield Footer()

    def on_mount(self) -> None:
        self.editor = self.query_one("#editor", RequestEditor)
        self.response = self.query_one("#response", ResponseViewer)
        self.collections = storage.load_enabled(self.data_dir)
        self.editor.load_from(self.current_request)

    # --- events ------------------------------------------------------------

    def on_request_editor_send_requested(self, event: RequestEditor.SendRequested) -> None:
        self.action_send()

    def on_request_editor_save_requested(self, event: RequestEditor.SaveRequested) -> None:
        self.action_save_request()

    def _load_request(self, collection_name: str, request_id: str) -> None:
        collection = next(
            (c for c in self.collections if c.name == collection_name), None
        )
        if collection is None:
            return
        saved = collection.requests.get(request_id)
        if saved is None:
            return
        self.current_saved = saved
        self.current_collection = collection
        self.current_request = deepcopy(saved.request)
        self.editor.load_from(self.current_request)
        self.editor.clear_token()
        self.notify(f"Loaded '{saved.name}'")

    # --- actions -----------------------------------------------------------

    def _sync_editor(self) -> RequestData:
        self.editor.apply_to(self.current_request)
        return self.current_request

    def action_send(self) -> None:
        request = self._sync_editor()
        if not request.url.strip():
            self.notify("Enter a URL first.", severity="error")
            return
        self.response.loading = True
        self.run_worker(self._do_send(request), exclusive=True)

    async def _do_send(self, request: RequestData) -> None:
        try:
            result = await send_request(
                request, oauth_provider=self.editor.oauth_provider
            )
        finally:
            self.response.loading = False
        self.last_request = request
        self.last_response = result
        self.response.show_response(result)
        if result.error:
            self.notify(result.error, severity="error")
        elif result.ok:
            self.notify(f"{result.status_code} in {result.elapsed_ms} ms", severity="information")
        else:
            self.notify(
                f"{result.status_code} {result.reason}".strip(),
                severity="warning",
            )

    def action_export_response(self) -> None:
        if self.last_response is None:
            self.notify("No response to export yet.", severity="warning")
            return
        request = self.last_request or self._sync_editor()
        name = (
            self.current_saved.name
            if self.current_saved is not None
            else self._default_request_name(self.current_request)
        )
        path = export_exchange(request, self.last_response, name, self.data_dir)
        self.notify(f"Exported to {path}")

    def action_share_request(self) -> None:
        request = self._sync_editor()
        if not request.url.strip():
            self.notify("Nothing to share — enter a URL first.", severity="warning")
            return
        name = (
            self.current_saved.name
            if self.current_saved is not None
            else self._default_request_name(self.current_request)
        )
        path = export_request_json(request, name, self.data_dir)
        self.notify(f"Shared request saved to {path}")

    def action_import_request(self) -> None:
        self.app.push_screen(ImportRequestModal(), self._on_import_result)

    def action_open_collections(self) -> None:
        self.app.push_screen(CollectionsPopup(self.collections), self._on_collections_popup)

    def _on_collections_popup(
        self, result: tuple[str, str] | str | None
    ) -> None:
        if result is None:
            return
        if result == NEW_COLLECTION:
            self.action_new_collection()
            return
        collection_name, request_id = result
        self._load_request(collection_name, request_id)

    def _on_import_result(self, result: tuple[str, RequestData] | None) -> None:
        if result is None:
            return
        name, request = result
        self.current_request = deepcopy(request)
        self.current_saved = None
        self.current_collection = None
        self.editor.load_from(self.current_request)
        self.editor.clear_token()
        self.response.reset()
        self.notify(f"Imported '{name}'")

    def action_save_request(self) -> None:
        request = self._sync_editor()
        if self.current_saved is not None and self.current_collection is not None:
            self.current_saved.request = deepcopy(request)
            storage.save_collection(self.current_collection, self.data_dir)
            self.notify(f"Saved '{self.current_saved.name}'")
            return
        name = self._default_request_name(request)
        choices = [c.name for c in self.collections]
        self.app.push_screen(SaveRequestModal(name, choices), self._on_save_result)

    def _on_save_result(self, result: SaveRequestResult | None) -> None:
        if result is None:
            return
        request = self._sync_editor()
        saved = SavedRequest(name=result.name, request=deepcopy(request))

        if result.create_new_collection:
            collection = Collection(name=result.collection_name)
            self.collections.append(collection)
        else:
            collection = next(
                (c for c in self.collections if c.name == result.collection_name), None
            )
            if collection is None:
                collection = Collection(name=result.collection_name)
                self.collections.append(collection)

        collection.requests[saved.id] = saved
        storage.save_collection(collection, self.data_dir)
        self.current_saved = saved
        self.current_collection = collection
        self.notify(f"Saved '{saved.name}' into '{collection.name}'")

    def action_new_collection(self) -> None:
        self.app.push_screen(NewCollectionModal(), self._on_new_collection)

    def _on_new_collection(self, name: str | None) -> None:
        if not name:
            return
        collection = Collection(name=name)
        self.collections.append(collection)
        storage.save_collection(collection, self.data_dir)
        self.notify(f"Created collection '{name}'")

    def action_new_request(self) -> None:
        self.current_saved = None
        self.current_collection = None
        self.current_request = RequestData()
        self.editor.load_from(self.current_request)
        self.editor.clear_token()
        self.response.reset()

    def action_delete_request(self) -> None:
        if self.current_saved is None or self.current_collection is None:
            self.notify("Nothing loaded to delete.", severity="warning")
            return
        name = self.current_saved.name
        self.current_collection.requests.pop(self.current_saved.id, None)
        if not self.current_collection.requests:
            self.collections = [
                c for c in self.collections if c is not self.current_collection
            ]
            storage.delete_collection(self.current_collection.name, self.data_dir)
        else:
            storage.save_collection(self.current_collection, self.data_dir)
        self.action_new_request()
        self.notify(f"Deleted '{name}'")

    @staticmethod
    def _default_request_name(request: RequestData) -> str:
        base = f"{request.method} {request.url}".strip()
        return base[:60] if base else "Untitled request"