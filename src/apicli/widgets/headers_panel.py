"""Headers editor: one 'Name: Value' per line in a TextArea."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Label, TextArea
from textual.widget import Widget


class HeadersPanel(Vertical):
    """Edit request headers, one ``Name: Value`` pair per line."""

    def compose(self) -> ComposeResult:
        yield Label("One header per line, as  name: value")
        yield TextArea(id="headers-text", classes="code-area")

    def on_mount(self) -> None:
        self._ta = self.query_one("#headers-text", TextArea)

    def set_headers(self, headers: list[list[str]]) -> None:
        self._ta.load_text("\n".join(f"{k}: {v}" for k, v in headers if k))

    def get_headers(self) -> list[list[str]]:
        pairs: list[list[str]] = []
        for line in self._ta.text.splitlines():
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            pairs.append([key.strip(), value.strip()])
        return pairs