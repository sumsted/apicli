"""apicli - a Postman-style API testing TUI built on Textual."""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding

from .screens.main_screen import MainScreen

CSS_PATH = Path(__file__).with_name("styles.tcss")


class ApiCliApp(App):
    """Terminal API client: collections, request editor, and response viewer."""

    TITLE = "apicli"
    SUB_TITLE = "API testing in the terminal"
    BINDINGS = [Binding("ctrl+q", "quit", "Quit")]
    CSS_PATH = CSS_PATH

    def on_mount(self) -> None:
        self.push_screen(MainScreen())


def main() -> None:
    ApiCliApp().run()


if __name__ == "__main__":
    main()