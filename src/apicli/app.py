"""apicli - a Postman-style API testing TUI built on Textual."""

from __future__ import annotations

import os
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding

from .screens.main_screen import MainScreen
from .theme import CYBERPUNK_THEME

CSS_PATH = Path(__file__).with_name("styles.tcss")

DEFAULT_THEME = "textual-dark"


class ApiCliApp(App):
    """Terminal API client: collections, request editor, and response viewer."""

    TITLE = "apicli"
    SUB_TITLE = "API testing in the terminal"
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+t", "toggle_theme", "Theme"),
    ]
    CSS_PATH = CSS_PATH
    # Free up ctrl+p for the collections popup.
    ENABLE_COMMAND_PALETTE: bool = False

    def __init__(self) -> None:
        super().__init__()
        self.register_theme(CYBERPUNK_THEME)
        self._base_theme = DEFAULT_THEME

    def on_mount(self) -> None:
        requested = os.environ.get("APICLI_THEME", "").strip()
        if requested in self.available_themes:
            self.theme = requested
        elif requested:
            self.notify(f"Unknown theme '{requested}'", severity="warning")
        self._base_theme = self.theme
        self.push_screen(MainScreen())

    def action_toggle_theme(self) -> None:
        if self.theme == CYBERPUNK_THEME.name:
            self.theme = (
                DEFAULT_THEME if self._base_theme == CYBERPUNK_THEME.name else self._base_theme
            )
        else:
            self._base_theme = self.theme
            self.theme = CYBERPUNK_THEME.name
        self.notify(f"Theme: {self.theme}")


def main() -> None:
    ApiCliApp().run()


if __name__ == "__main__":
    main()