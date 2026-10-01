"""Tests for the pywebview desktop shell (headless parts only)."""

from __future__ import annotations

import sys
import types

import httpx
import pytest

from apicli import desktop


def _fake_webview(dialog_result):
    window = types.SimpleNamespace(create_file_dialog=lambda *a, **k: dialog_result)
    return types.SimpleNamespace(
        windows=[window],
        FileDialog=types.SimpleNamespace(OPEN=10, SAVE=30),
    )


def test_free_port_is_usable():
    port = desktop.free_port()
    assert 0 < port < 65536


@pytest.mark.asyncio
async def test_desktop_server_enforces_session_token(tmp_path, monkeypatch):
    monkeypatch.setenv("APICLI_DATA_DIR", str(tmp_path))
    token = "session-token"
    port = desktop.free_port()
    server = desktop._start_server(token, port)
    try:
        async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}") as client:
            unauthorized = await client.get("/api/collections")
            assert unauthorized.status_code == 401

            authorized = await client.get(
                "/api/collections",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert authorized.status_code == 200
    finally:
        server.should_exit = True


def test_desktop_api_save_text_accepts_string_path(tmp_path, monkeypatch):
    # macOS returns a bare string from the save dialog.
    target = tmp_path / "report.txt"
    monkeypatch.setitem(sys.modules, "webview", _fake_webview(str(target)))

    result = desktop.DesktopApi().save_text("report.txt", "hello world")

    assert result == str(target)
    assert target.read_text(encoding="utf-8") == "hello world"


def test_desktop_api_save_text_accepts_tuple_path(tmp_path, monkeypatch):
    # Windows/Linux return a tuple.
    target = tmp_path / "report.txt"
    monkeypatch.setitem(sys.modules, "webview", _fake_webview([str(target)]))

    result = desktop.DesktopApi().save_text("report.txt", "hi")

    assert result == str(target)
    assert target.read_text(encoding="utf-8") == "hi"


def test_desktop_api_open_text(tmp_path, monkeypatch):
    source = tmp_path / "shared.json"
    source.write_text('{"method": "GET"}', encoding="utf-8")
    monkeypatch.setitem(sys.modules, "webview", _fake_webview([str(source)]))

    result = desktop.DesktopApi().open_text()

    assert result == {"name": "shared.json", "content": '{"method": "GET"}'}


def test_selected_path_normalization():
    pick = desktop.DesktopApi._selected_path
    assert pick(None) is None
    assert pick("") is None
    assert pick("/tmp/out.txt") == "/tmp/out.txt"
    assert pick(["/tmp/out.txt"]) == "/tmp/out.txt"
    assert pick(("/tmp/a.json", "/tmp/b.json")) == "/tmp/a.json"
    assert pick([]) is None


def test_desktop_api_cancelled_dialogs(monkeypatch):
    monkeypatch.setitem(sys.modules, "webview", _fake_webview(None))
    api = desktop.DesktopApi()

    assert api.save_text("x.txt", "data") is None
    assert api.open_text() is None
