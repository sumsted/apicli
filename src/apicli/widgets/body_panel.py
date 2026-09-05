"""Body editor: body type selector + text area."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Label, Select, TextArea

from ..export import pretty_json
from ..models import BODY_TYPES, RequestData

_LANGUAGES = {"json": "json", "xml": "xml"}


class BodyPanel(Vertical):
    """Edit the request body."""

    def compose(self) -> ComposeResult:
        yield Label("Body")
        with Horizontal(id="body-controls"):
            yield Select(
                [(t.upper(), t) for t in BODY_TYPES],
                value="json",
                id="body-type",
            )
        yield TextArea(id="body-text", classes="code-area")

    def on_mount(self) -> None:
        self._type = self.query_one("#body-type", Select)
        self._ta = self.query_one("#body-text", TextArea)

    def load_from(self, request: RequestData) -> None:
        body_type = request.body_type if request.body_type in BODY_TYPES else "text"
        self._type.value = body_type
        self._set_language(body_type)
        body = request.body
        if body_type == "json":
            body = pretty_json(body)
        self._ta.load_text(body)

    def apply_to(self, request: RequestData) -> None:
        request.body_type = self.selected_type
        request.body = self._ta.text

    @property
    def selected_type(self) -> str:
        value = self._type.value
        if value is None or value is Select.NULL:
            return "text"
        return str(value)

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "body-type" and event.value is not Select.NULL:
            self._set_language(str(event.value))

    def _set_language(self, body_type: str) -> None:
        language = _LANGUAGES.get(body_type, "")
        try:
            self._ta.language = language
        except ValueError:
            pass