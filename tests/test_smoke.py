"""Smoke tests: boot the TUI headlessly and drive the request flow."""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager

import httpx
import pytest

from textual.css.query import NoMatches
from textual.widgets import TextArea

from apicli.app import ApiCliApp
from apicli.client import send_request
from apicli.models import (
    AuthConfig,
    BasicAuthConfig,
    OAuth2ClientCredentialsConfig,
    RequestData,
    ResponseData,
)
from apicli.auth import OAuth2Provider


async def wait_for_widget(app, selector, timeout: float = 5.0):
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        try:
            return app.screen.query_one(selector)
        except NoMatches:
            await asyncio.sleep(0.02)
    raise AssertionError(f"Widget {selector!r} never appeared")


@asynccontextmanager
async def boot_app(size=(140, 44)):
    app = ApiCliApp()
    async with app.run_test(size=size) as pilot:
        await wait_on_screen(app, "#editor")
        yield app, pilot


async def wait_on_screen(app, selector, timeout: float = 5.0):
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        try:
            return app.screen.query_one(selector)
        except NoMatches:
            await asyncio.sleep(0.02)
    raise AssertionError(f"Widget {selector!r} never appeared")


@pytest.mark.asyncio
async def test_app_boots_and_composes():
    async with boot_app() as (app, pilot):
        assert app.screen.query_one("#editor") is not None
        assert app.screen.query_one("#response") is not None
        assert app.screen.query_one("#url-input") is not None
        # Collections are now a popup, not on the main screen.
        try:
            app.screen.query_one("#collections")
        except NoMatches:
            pass
        else:
            raise AssertionError("#collections should not be on the main screen")

        editor = app.screen.query_one("#editor")
        response = app.screen.query_one("#response")
        assert editor.size.width == response.size.width
        assert editor.size.height == response.size.height

        from textual.widgets import TabbedContent

        req_tabs = editor.query_one(TabbedContent)
        assert req_tabs.active_pane is not None
        assert req_tabs.active_pane.id == "tab-body"

        # Open the collections popup.
        await pilot.press("ctrl+p")
        await pilot.pause()
        from apicli.screens.collections_popup import CollectionsPopup

        assert isinstance(app.screen, CollectionsPopup)
        assert app.screen.query_one("#collections") is not None
        assert app.screen.query_one("#popup-new-collection") is not None
        box = app.screen.query_one("#collections-popup")
        assert box.region.x + box.region.width // 2 < app.screen.size.width * 0.60
        assert box.region.x > 10 and box.region.y > 0


@pytest.mark.asyncio
async def test_send_updates_response_viewer(monkeypatch):
    async def fake_send(request, oauth_provider=None, timeout=60.0):
        return ResponseData(
            status_code=200,
            reason="OK",
            http_version="HTTP/1.1",
            headers=[("content-type", "application/json")],
            body=b'{"ok": true}',
            elapsed_ms=42,
            size_bytes=12,
            ok=True,
            url=request.url,
            request_method=request.method,
        )

    monkeypatch.setattr("apicli.screens.main_screen.send_request", fake_send)
    async with boot_app() as (app, pilot):
        editor = app.screen.query_one("#editor")
        editor.url_input.value = "https://example.com/x"
        await pilot.press("ctrl+r")
        await pilot.pause()
        status = app.screen.query_one("#response-status")
        assert "200" in status.render().plain
        body = app.screen.query_one("#response-body", TextArea)
        assert '"ok": true' in body.text
        assert "'ok': True" not in body.text
        assert body.read_only


@pytest.mark.asyncio
async def test_response_body_is_scrollable(monkeypatch):
    body = json.dumps({f"key_{i}": i for i in range(100)}, indent=2).encode()

    async def fake_send(request, oauth_provider=None, timeout=60.0):
        return ResponseData(
            status_code=200,
            reason="OK",
            http_version="HTTP/1.1",
            headers=[("content-type", "application/json")],
            body=body,
            elapsed_ms=5,
            size_bytes=len(body),
            ok=True,
            url=request.url,
            request_method=request.method,
        )

    monkeypatch.setattr("apicli.screens.main_screen.send_request", fake_send)
    async with boot_app() as (app, pilot):
        app.screen.query_one("#editor").url_input.value = "https://example.com/x"
        await pilot.press("ctrl+r")
        await pilot.pause()

        scroll = app.screen.query_one("#response-body", TextArea)
        assert scroll.max_scroll_y > 0


@pytest.mark.asyncio
async def test_response_body_can_be_selected_and_copied(monkeypatch):
    async def fake_send(request, oauth_provider=None, timeout=60.0):
        return ResponseData(
            status_code=200,
            reason="OK",
            http_version="HTTP/1.1",
            headers=[("content-type", "application/json")],
            body=b'{"a": [1, 2], "b": true}',
            elapsed_ms=5,
            size_bytes=24,
            ok=True,
            url=request.url,
            request_method=request.method,
        )

    monkeypatch.setattr("apicli.screens.main_screen.send_request", fake_send)
    async with boot_app() as (app, pilot):
        app.screen.query_one("#editor").url_input.value = "https://example.com/x"
        await pilot.press("ctrl+r")
        await pilot.pause()

        body = app.screen.query_one("#response-body", TextArea)
        assert body.selected_text == ""
        body.action_select_all()
        copied = body.selected_text
        assert copied
        assert '"a": [' in copied
        assert '"b": true' in copied
        assert json.loads(copied) == {"a": [1, 2], "b": True}


@pytest.mark.asyncio
async def test_request_body_textarea_scrolls():
    async with boot_app() as (app, pilot):
        editor = app.screen.query_one("#editor")
        editor.body_panel._ta.load_text("\n".join(f"line {i}" for i in range(200)))
        await pilot.pause()
        ta = app.screen.query_one("#body-text")
        assert ta.max_scroll_y > 0


@pytest.mark.asyncio
async def test_request_tabs_all_scroll():
    from apicli.widgets.auth_panel import AuthPanel
    from textual.widgets import TabbedContent

    async with boot_app(size=(120, 22)) as (app, pilot):
        editor = app.screen.query_one("#editor")
        tabs = editor.query_one(TabbedContent)
        assert tabs.region.bottom <= editor.region.bottom

        editor.headers_panel._ta.load_text("\n".join(f"h {i}" for i in range(60)))
        editor.body_panel._ta.load_text("\n".join(f"b {i}" for i in range(60)))
        editor.auth_panel._type.value = "oauth2"

        tabs.active = "tab-headers"
        await pilot.pause()
        assert editor.headers_panel._ta.max_scroll_y > 0

        tabs.active = "tab-body"
        await pilot.pause()
        assert editor.body_panel._ta.max_scroll_y > 0

        tabs.active = "tab-auth"
        await pilot.pause()
        auth = editor.auth_panel
        assert isinstance(auth, AuthPanel)
        assert auth.max_scroll_y > 0
        auth.scroll_end()
        await pilot.pause()
        assert auth.max_scroll_y > 0


@pytest.mark.asyncio
async def test_send_errors_do_not_crash(monkeypatch):
    async def fake_send(request, oauth_provider=None, timeout=60.0):
        return ResponseData(url=request.url, request_method=request.method, error="boom")

    monkeypatch.setattr("apicli.screens.main_screen.send_request", fake_send)
    async with boot_app() as (app, pilot):
        app.screen.query_one("#editor").url_input.value = "https://example.com/x"
        await pilot.press("ctrl+r")
        await pilot.pause()
        status = app.screen.query_one("#response-status")
        assert "boom" in status.render().plain


@pytest.mark.asyncio
async def test_export_keybinding_writes_file(tmp_path, monkeypatch):
    from apicli.models import TimelineEvent

    async def fake_send(request, oauth_provider=None, timeout=60.0):
        return ResponseData(
            status_code=200,
            reason="OK",
            http_version="HTTP/1.1",
            headers=[("content-type", "application/json")],
            body=b'{"ok": true}',
            elapsed_ms=42,
            size_bytes=12,
            ok=True,
            url=request.url,
            request_method=request.method,
            sent_headers=[("content-type", "application/json")],
            sent_body=None,
            timeline=[
                TimelineEvent("request prepared", 0),
                TimelineEvent("request sent", 4),
                TimelineEvent("response body read", 42),
                TimelineEvent("complete", 42),
            ],
        )

    monkeypatch.setenv("APICLI_DATA_DIR", str(tmp_path))
    monkeypatch.setattr("apicli.screens.main_screen.send_request", fake_send)

    async with boot_app() as (app, pilot):
        app.screen.query_one("#editor").url_input.value = "https://example.com/x"
        await pilot.press("ctrl+r")
        await pilot.pause()
        await pilot.press("ctrl+e")
        await pilot.pause()

        exports = list((tmp_path / "exports").glob("*.txt"))
        assert exports, "expected an exported report"
        text = exports[0].read_text(encoding="utf-8")
        assert "https://example.com/x" in text
        assert "TIMELINE" in text
        assert "complete" in text


@pytest.mark.asyncio
async def test_share_keybinding_writes_request_json(tmp_path, monkeypatch):
    monkeypatch.setenv("APICLI_DATA_DIR", str(tmp_path))

    async with boot_app() as (app, pilot):
        editor = app.screen.query_one("#editor")
        editor.url_input.value = "https://api.example.com/items"
        editor.body_panel._ta.load_text('{"a": 1}')
        await pilot.pause()
        await pilot.press("ctrl+shift+e")
        await pilot.pause()

        exports = list((tmp_path / "exports").glob("*.json"))
        assert exports, "expected a shared request JSON"
        payload = json.loads(exports[0].read_text(encoding="utf-8"))
        assert payload["request"]["url"] == "https://api.example.com/items"


@pytest.mark.asyncio
async def test_import_keybinding_loads_shared_request(tmp_path, monkeypatch):
    import datetime

    from apicli.models import RequestData
    from apicli.screens.import_request import ImportRequestModal
    from apicli.share import export_request_json
    from textual.widgets import Button, Input

    shared = export_request_json(
        RequestData(
            method="POST",
            url="https://shared.example.com/go",
            body='{"x": 1}',
            body_type="json",
        ),
        "Shared Thing",
        tmp_path,
        timestamp=datetime.datetime(2026, 1, 2, 3, 4, 5),
    )

    async with boot_app() as (app, pilot):
        await pilot.press("ctrl+i")
        await pilot.pause()
        assert isinstance(app.screen, ImportRequestModal)

        modal = app.screen
        modal.query_one("#import-path", Input).value = str(shared)
        modal.query_one("#import-confirm", Button).press()
        await pilot.pause()

        editor = app.screen.query_one("#editor")
        assert editor.url_input.value == "https://shared.example.com/go"
        assert editor.body_panel._ta.text == '{\n  "x": 1\n}'


@pytest.mark.asyncio
async def test_loaded_json_body_is_pretty_formatted():
    from apicli.models import RequestData

    async with boot_app() as (app, pilot):
        request = RequestData(
            method="POST",
            url="https://api.example.com/items",
            body='{"b":1,"a":[1,2]}',
            body_type="json",
        )
        app.screen.editor.load_from(request)
        text = app.screen.editor.body_panel._ta.text
        assert '"a": [' in text
        assert '"b": 1' in text
        assert text.strip().startswith("{\n")


@pytest.mark.asyncio
async def test_json_body_uses_syntax_highlighting():
    from apicli.models import RequestData
    from textual.document._syntax_aware_document import SyntaxAwareDocument

    async with boot_app() as (app, pilot):
        request = RequestData(
            method="POST",
            url="https://api.example.com/items",
            body='{"a": true}',
            body_type="json",
        )
        app.screen.editor.load_from(request)
        await pilot.pause()
        ta = app.screen.editor.body_panel._ta
        assert isinstance(ta.document, SyntaxAwareDocument)


class _JsonTransport:
    """Exchange /token for /api: OAuth2 client-credentials end to end."""

    def __init__(self):
        self.calls = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.calls.append((request.method, request.url.path, dict(request.headers)))
        if request.url.path == "/token":
            assert request.content
            body = request.content.decode()
            assert "grant_type=client_credentials" in body
            assert "client_id=cid" in body and "client_secret=csec" in body
            return httpx.Response(
                200,
                json={"access_token": "tok123", "token_type": "Bearer", "expires_in": 3600},
            )
        authorization = request.headers.get("authorization")
        if authorization == "Bearer tok123":
            return httpx.Response(200, json={"access": "granted"})
        return httpx.Response(401, json={"access": "denied"})


@pytest.mark.asyncio
async def test_oauth2_client_credentials_end_to_end(monkeypatch):
    transport = _JsonTransport()

    class MockedAsyncClient(httpx.AsyncClient):
        def __init__(self, **kwargs):
            super().__init__(**kwargs, transport=httpx.MockTransport(transport.handler))

    monkeypatch.setattr("apicli.client.httpx.AsyncClient", MockedAsyncClient)

    request = RequestData(url="https://example.com/api")
    request.auth = AuthConfig(
        type="oauth2",
        oauth2=OAuth2ClientCredentialsConfig(
            token_url="https://example.com/token",
            client_id="cid",
            client_secret="csec",
        ),
    )
    provider = OAuth2Provider(request.auth.oauth2)
    response = await send_request(request, oauth_provider=provider)

    assert response.status_code == 200
    assert json.loads(response.text)["access"] == "granted"
    assert (transport.calls[0][0], transport.calls[0][1]) == ("POST", "/token")
    assert (transport.calls[1][0], transport.calls[1][1]) == ("GET", "/api")
    authorization = transport.calls[1][2].get("authorization", "")
    assert authorization.lower() == "bearer tok123"


@pytest.mark.asyncio
async def test_basic_auth_header(monkeypatch):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers.get("authorization")
        return httpx.Response(200, text="hi")

    class MockedAsyncClient(httpx.AsyncClient):
        def __init__(self, **kwargs):
            super().__init__(**kwargs, transport=httpx.MockTransport(handler))

    monkeypatch.setattr("apicli.client.httpx.AsyncClient", MockedAsyncClient)

    request = RequestData(url="https://example.com/x")
    request.auth = AuthConfig(
        type="basic", basic=BasicAuthConfig(username="user", password="pass")
    )
    response = await send_request(request)
    assert response.status_code == 200
    assert captured["authorization"].startswith("Basic ")


@pytest.mark.asyncio
async def test_oauth2_token_is_cached(monkeypatch):
    total_hits = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        total_hits["count"] += 1
        return httpx.Response(
            200, json={"access_token": "t", "token_type": "Bearer", "expires_in": 120}
        )

    class MockedAsyncClient(httpx.AsyncClient):
        def __init__(self, **kwargs):
            super().__init__(**kwargs, transport=httpx.MockTransport(handler))

    monkeypatch.setattr("apicli.auth.httpx.AsyncClient", MockedAsyncClient)

    config = OAuth2ClientCredentialsConfig(
        token_url="https://example.com/token", client_id="c", client_secret="s"
    )
    provider = OAuth2Provider(config)
    async with MockedAsyncClient() as client:
        first = await provider.get_token(client)
        second = await provider.get_token(client)
    assert first.access_token == second.access_token == "t"
    assert total_hits["count"] == 1