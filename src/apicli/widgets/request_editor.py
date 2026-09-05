"""Request editor: URL bar + method + headers/body/auth tabs."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import (
    Button,
    Input,
    Select,
    Static,
    TabbedContent,
    TabPane,
)

from ..models import HTTP_METHODS, RequestData
from .auth_panel import AuthPanel
from .body_panel import BodyPanel
from .headers_panel import HeadersPanel


class RequestEditor(Vertical):
    """The request building pane."""

    class SendRequested(Message):
        pass

    class SaveRequested(Message):
        pass

    def compose(self) -> ComposeResult:
        with Horizontal(id="urlbar"):
            yield Select([(m, m) for m in HTTP_METHODS], value="GET", id="method")
            yield Input(placeholder="https://api.example.com/path", id="url-input")
            yield Static("No Auth", id="auth-badge")
            yield Button("Save", id="save-button", variant="default")
            yield Button("Send", id="send-button", variant="primary")
        with TabbedContent(id="req-tabs") as tabs:
            with TabPane("Headers", id="tab-headers"):
                yield HeadersPanel(id="headers-panel")
            with TabPane("Body", id="tab-body"):
                yield BodyPanel(id="body-panel")
            with TabPane("Auth", id="tab-auth"):
                yield AuthPanel(id="auth-panel")

    def on_mount(self) -> None:
        self.method_select = self.query_one("#method", Select)
        self.url_input = self.query_one("#url-input", Input)
        self.auth_badge = self.query_one("#auth-badge", Static)
        self.send_button = self.query_one("#send-button", Button)
        self.save_button = self.query_one("#save-button", Button)
        self.headers_panel = self.query_one("#headers-panel", HeadersPanel)
        self.body_panel = self.query_one("#body-panel", BodyPanel)
        self.auth_panel = self.query_one("#auth-panel", AuthPanel)
        self.border_title = "Request"

    def load_from(self, request: RequestData) -> None:
        self.method_select.value = request.method if request.method in HTTP_METHODS else "GET"
        self.url_input.value = request.url
        self.headers_panel.set_headers(request.headers)
        self.body_panel.load_from(request)
        self.auth_panel.load_from(request.auth)
        self._update_badge()

    def apply_to(self, request: RequestData) -> None:
        request.method = str(self.method_select.value)
        request.url = self.url_input.value.strip()
        request.headers = self.headers_panel.get_headers()
        self.body_panel.apply_to(request)
        self.auth_panel.apply_to(request.auth)
        self._update_badge()

    def clear_token(self) -> None:
        self.auth_panel.clear_token()

    @property
    def oauth_provider(self):
        return self.auth_panel.provider

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "send-button":
            self.post_message(self.SendRequested())
        elif event.button.id == "save-button":
            self.post_message(self.SaveRequested())

    def on_select_changed(self, event: Select.Changed) -> None:
        self._update_badge()

    def _update_badge(self) -> None:
        try:
            if self.auth_panel.selected_type == "none":
                self.auth_badge.update("No Auth")
            elif self.auth_panel.selected_type == "basic":
                self.auth_badge.update("Basic Auth")
            else:
                self.auth_badge.update("OAuth2 client-credentials")
        except Exception:
            pass