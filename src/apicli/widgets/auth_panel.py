"""Auth editor: none / basic / OAuth2 client-credentials."""

from __future__ import annotations

import httpx
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import Button, Checkbox, Input, Label, Select, Static

from ..auth import AuthError, OAuth2Provider
from ..models import AUTH_TYPES, AuthConfig, OAuth2ClientCredentialsConfig

AUTH_LABELS = {
    "none": "No Auth",
    "basic": "Basic Auth",
    "oauth2": "OAuth2 (client credentials)",
}


class AuthPanel(VerticalScroll):
    """Edit auth config and drive the OAuth2 token lifecycle."""

    class AuthChanged(Message):
        """The selected auth type changed."""

        def __init__(self, auth_type: str) -> None:
            self.auth_type = auth_type
            super().__init__()

    class TokenObtained(Message):
        """A token endpoint returned a token (or failed)."""

        def __init__(self, ok: bool, detail: str) -> None:
            self.ok = ok
            self.detail = detail
            super().__init__()

    def compose(self) -> ComposeResult:
        yield Label("Auth")
        yield Select(
            [(AUTH_LABELS[t], t) for t in AUTH_TYPES],
            value="none",
            id="auth-type",
        )

        with Vertical(id="basic-fields", classes="auth-fields"):
            yield Label("Username")
            yield Input(placeholder="username", id="basic-username")
            yield Label("Password")
            yield Input(placeholder="password", password=True, id="basic-password")

        with Vertical(id="oauth2-fields", classes="auth-fields"):
            yield Label("Token URL")
            yield Input(
                placeholder="https://idp.example.com/oauth/token",
                id="oauth-token-url",
            )
            yield Label("Client ID")
            yield Input(placeholder="client id", id="oauth-client-id")
            yield Label("Client Secret")
            yield Input(placeholder="client secret", password=True, id="oauth-client-secret")
            yield Label("Scope (optional)")
            yield Input(placeholder="read write", id="oauth-scope")
            yield Checkbox(
                "Send client credentials in request body",
                value=True,
                id="oauth-in-body",
            )
            with Horizontal(id="oauth-actions"):
                yield Button("Get token", id="oauth-get-token", variant="primary")
                yield Static("No token", id="oauth-status")

    def on_mount(self) -> None:
        self._type = self.query_one("#auth-type", Select)
        self._basic = self.query_one("#basic-fields")
        self._oauth2 = self.query_one("#oauth2-fields")
        self._basic_username = self.query_one("#basic-username", Input)
        self._basic_password = self.query_one("#basic-password", Input)
        self._token_url = self.query_one("#oauth-token-url", Input)
        self._client_id = self.query_one("#oauth-client-id", Input)
        self._client_secret = self.query_one("#oauth-client-secret", Input)
        self._scope = self.query_one("#oauth-scope", Input)
        self._in_body = self.query_one("#oauth-in-body", Checkbox)
        self._status = self.query_one("#oauth-status", Static)
        self._provider: OAuth2Provider | None = None
        self._show_fields()

    @property
    def selected_type(self) -> str:
        value = self._type.value
        if value is None or value is Select.NULL:
            return "none"
        return str(value)

    @property
    def provider(self) -> OAuth2Provider | None:
        return self._provider

    def load_from(self, auth: AuthConfig) -> None:
        self._type.value = auth.type
        self._basic_username.value = auth.basic.username
        self._basic_password.value = auth.basic.password
        self._token_url.value = auth.oauth2.token_url
        self._client_id.value = auth.oauth2.client_id
        self._client_secret.value = auth.oauth2.client_secret
        self._scope.value = auth.oauth2.scope
        self._in_body.value = auth.oauth2.include_client_credentials_in_body
        self._show_fields()
        self._rebuild_provider()

    def apply_to(self, auth: AuthConfig) -> None:
        auth.type = self.selected_type
        auth.basic.username = self._basic_username.value
        auth.basic.password = self._basic_password.value
        auth.oauth2.token_url = self._token_url.value
        auth.oauth2.client_id = self._client_id.value
        auth.oauth2.client_secret = self._client_secret.value
        auth.oauth2.scope = self._scope.value
        auth.oauth2.include_client_credentials_in_body = bool(self._in_body.value)
        self._rebuild_provider()

    def clear_token(self) -> None:
        if self._provider is not None:
            self._provider.clear()
            self._set_status("No token", muted=True)

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "auth-type":
            self._show_fields()
            self._rebuild_provider()
            self.clear_token()
            self.post_message(self.AuthChanged(self.selected_type))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "oauth-get-token":
            self.run_worker(self._fetch_token(), exclusive=True)

    async def _fetch_token(self) -> None:
        provider = self._ensure_provider()
        if provider is None:
            self._set_status("Fill in token URL, client ID and secret", error=True)
            return
        self._set_status("Fetching token…", muted=True)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                await provider.get_token(client)
        except AuthError as exc:
            self._set_status(f"Failed: {exc}", error=True)
            self.post_message(self.TokenObtained(False, str(exc)))
            return
        except httpx.TransportError as exc:
            self._set_status(f"Failed: {exc}", error=True)
            self.post_message(self.TokenObtained(False, str(exc)))
            return
        self._set_status("Token ready", ok=True)
        self.post_message(self.TokenObtained(True, ""))

    def _ensure_provider(self) -> OAuth2Provider | None:
        if self.selected_type != "oauth2":
            return None
        self._rebuild_provider()
        return self._provider

    def _rebuild_provider(self) -> None:
        if not hasattr(self, "_token_url"):
            return
        config = self._current_oauth_config()
        if self.selected_type == "oauth2" and config.token_url and config.client_id:
            self._provider = OAuth2Provider(config)
        else:
            self._provider = None

    def _current_oauth_config(self) -> OAuth2ClientCredentialsConfig:
        return OAuth2ClientCredentialsConfig(
            token_url=self._token_url.value,
            client_id=self._client_id.value,
            client_secret=self._client_secret.value,
            scope=self._scope.value,
            include_client_credentials_in_body=bool(self._in_body.value),
        )

    def _show_fields(self) -> None:
        selected = self.selected_type
        self._basic.display = selected == "basic"
        self._oauth2.display = selected == "oauth2"

    def _set_status(
        self,
        text: str,
        *,
        muted: bool = False,
        ok: bool = False,
        error: bool = False,
    ) -> None:
        classes = []
        if muted:
            classes.append("-muted")
        if ok:
            classes.append("-ok")
        if error:
            classes.append("-error")
        self._status.set_classes(" ".join(classes))
        self._status.update(text)