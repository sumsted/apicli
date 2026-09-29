"""Tests for the optional cyberpunk theme."""

from __future__ import annotations

import pytest

from apicli.app import DEFAULT_THEME, ApiCliApp
from apicli.theme import CYBERPUNK_THEME

from test_smoke import boot_app


def test_cyberpunk_theme_is_registered():
    app = ApiCliApp()
    assert "cyberpunk" in app.available_themes
    assert app.available_themes["cyberpunk"] is CYBERPUNK_THEME


@pytest.mark.asyncio
async def test_toggle_theme_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("APICLI_DATA_DIR", str(tmp_path))
    async with boot_app() as (app, pilot):
        assert app.theme == DEFAULT_THEME

        await pilot.press("ctrl+t")
        await pilot.pause()
        assert app.theme == "cyberpunk"

        await pilot.press("ctrl+t")
        await pilot.pause()
        assert app.theme == DEFAULT_THEME


@pytest.mark.asyncio
async def test_theme_selected_from_env(tmp_path, monkeypatch):
    monkeypatch.setenv("APICLI_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("APICLI_THEME", "cyberpunk")
    async with boot_app() as (app, pilot):
        assert app.theme == "cyberpunk"

        # Toggling away from cyberpunk falls back to the default scheme.
        await pilot.press("ctrl+t")
        await pilot.pause()
        assert app.theme == DEFAULT_THEME


@pytest.mark.asyncio
async def test_unknown_theme_env_falls_back_and_warns(tmp_path, monkeypatch):
    monkeypatch.setenv("APICLI_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("APICLI_THEME", "not-a-theme")
    async with boot_app() as (app, pilot):
        assert app.theme == DEFAULT_THEME
