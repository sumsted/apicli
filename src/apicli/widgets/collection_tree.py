"""Collections sidebar: a tree of collections and their saved requests."""

from __future__ import annotations

from textual.message import Message
from textual.widgets import Tree

from ..models import Collection, SavedRequest

REQUEST_EMOJI = {"GET": "🟢", "POST": "🟡", "PUT": "🔵", "PATCH": "🟣", "DELETE": "🔴", "HEAD": "⚪", "OPTIONS": "⚪"}


class CollectionTree(Tree[dict]):
    """Tree where collection nodes carry {'kind': 'collection', 'name': str}
    and request nodes carry {'kind': 'request', 'request_id': str, 'collection_name': str}."""

    class RequestSelected(Message):
        def __init__(self, collection_name: str, request_id: str) -> None:
            self.collection_name = collection_name
            self.request_id = request_id
            super().__init__()

    def __init__(self, *args, **kwargs) -> None:
        super().__init__("Collections", *args, **kwargs)

    def on_mount(self) -> None:
        self.root.label = "Collections"
        self.root.expand()
        self.border_title = "Collections"

    def apply_data(self, collections: list[Collection]) -> None:
        """Rebuild the tree from the current list of collections."""
        self.clear()
        self.root.label = "Collections"
        for collection in collections:
            col_node = self.root.add(
                collection.name,
                data={"kind": "collection", "name": collection.name},
            )
            col_node.expand()
            for request in collection.requests.values():
                col_node.add(
                    self._request_label(request),
                    data={
                        "kind": "request",
                        "request_id": request.id,
                        "collection_name": collection.name,
                    },
                )

    @staticmethod
    def _request_label(request: SavedRequest) -> str:
        emoji = REQUEST_EMOJI.get(request.request.method, "◻")
        return f"{emoji} {request.name}"

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        data: dict | None = event.node.data
        if not data or data.get("kind") != "request":
            return
        self.post_message(
            self.RequestSelected(
                collection_name=data["collection_name"],
                request_id=data["request_id"],
            )
        )