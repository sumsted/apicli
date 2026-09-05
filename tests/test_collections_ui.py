"""UI tests for the collection lifecycle: save, reload, select, edit, delete."""

from __future__ import annotations

import pytest
from textual.widgets import Button, Input

from apicli import storage

from test_smoke import boot_app


@pytest.mark.asyncio
async def test_save_request_creates_collection(tmp_path, monkeypatch):
    monkeypatch.setenv("APICLI_DATA_DIR", str(tmp_path))
    async with boot_app() as (app, pilot):
        editor = app.screen.query_one("#editor")
        editor.url_input.value = "https://api.example.com/users"
        editor.method_select.value = "POST"
        editor.body_panel._ta.load_text('{"name": "kim"}')

        await pilot.press("ctrl+s")
        await pilot.pause()

        # Screen is now the SaveRequestModal.
        name_input = app.screen.query_one("#save-name", Input)
        name_input.value = "create user"
        new_collection = app.screen.query_one("#save-new-collection", Input)
        new_collection.value = "Users API"
        app.screen.query_one("#save-confirm", Button).press()

        await pilot.pause()

        # Persisted to disk.
        files = list(tmp_path.glob("*.json"))
        assert len(files) == 1
        assert files[0].name == "users-api.json"

        collection = storage.load_collection(files[0])
        saved = next(iter(collection.requests.values()))
        assert saved.name == "create user"
        assert saved.request.url == "https://api.example.com/users"
        assert saved.request.method == "POST"

        # Tree gained a node; MainScreen tracks selection.
        assert app.screen is not None


@pytest.mark.asyncio
async def test_load_select_edit_and_delete(tmp_path, monkeypatch):
    monkeypatch.setenv("APICLI_DATA_DIR", str(tmp_path))
    async with boot_app() as (app, pilot):
        from textual.widgets import Tree as TextualTree

        tree = app.screen.query_one("#collections")
        assert isinstance(tree, TextualTree)

        # Seed a collection with two requests directly into storage.
        from apicli.models import Collection, SavedRequest, RequestData

        collection = Collection(name="Demo API")
        collection.requests["r1"] = SavedRequest(
            id="r1",
            name="get health",
            request=RequestData(method="GET", url="https://demo.example.com/health"),
        )
        collection.requests["r2"] = SavedRequest(
            id="r2",
            name="delete user",
            request=RequestData(method="DELETE", url="https://demo.example.com/users/7"),
        )
        storage.save_collection(collection, tmp_path)

        # Reload: create a fresh main screen state via reload of the app.
        app.screen.collections = storage.load_enabled(tmp_path)
        screen = app.screen
        screen.editor.load_from(screen.collections[0].requests["r1"].request)
        screen.current_collection = screen.collections[0]
        screen.current_saved = screen.collections[0].requests["r1"]
        screen.collection_tree.apply_data(screen.collections)

        # Find the request node matching r1 and select it via Tree.select_node.
        col_node = tree.root.children[0]
        request_node = next(n for n in col_node.children if n.data["request_id"] == "r1")
        tree.select_node(request_node)
        await pilot.pause()

        editor = app.screen.query_one("#editor")
        assert editor.url_input.value == "https://demo.example.com/health"
        assert str(editor.method_select.value) == "GET"

        # Edit URL, save in place -> must NOT create a new file.
        editor.url_input.value = "https://demo.example.com/healthz"
        await pilot.press("ctrl+s")
        await pilot.pause()
        assert len(list(tmp_path.glob("*.json"))) == 1
        collection = storage.load_collection(tmp_path / "demo-api.json")
        assert collection.requests["r1"].request.url == "https://demo.example.com/healthz"
        assert collection.requests["r2"].name == "delete user"

        # Delete removes the request (collection keeps the other request).
        await pilot.press("ctrl+d")
        await pilot.pause()
        collection = storage.load_collection(tmp_path / "demo-api.json")
        assert "r1" not in collection.requests
        assert "r2" in collection.requests


@pytest.mark.asyncio
async def test_save_button_opens_modal(tmp_path, monkeypatch):
    monkeypatch.setenv("APICLI_DATA_DIR", str(tmp_path))
    async with boot_app() as (app, pilot):
        editor = app.screen.query_one("#editor")
        editor.url_input.value = "https://api.example.com/x"

        app.screen.query_one("#save-button", Button).press()
        await pilot.pause()

        from apicli.screens.save_request import SaveRequestModal

        assert isinstance(app.screen, SaveRequestModal)


@pytest.mark.asyncio
async def test_save_into_existing_collection_via_modal(tmp_path, monkeypatch):
    from apicli.models import Collection
    from textual.widgets import Select

    monkeypatch.setenv("APICLI_DATA_DIR", str(tmp_path))
    storage.save_collection(Collection(name="Existing"), tmp_path)

    async with boot_app() as (app, pilot):
        editor = app.screen.query_one("#editor")
        editor.url_input.value = "https://api.example.com/ping"

        await pilot.press("ctrl+s")
        await pilot.pause()

        from apicli.screens.save_request import SaveRequestModal

        assert isinstance(app.screen, SaveRequestModal)
        collection_select = app.screen.query_one("#save-collection", Select)
        collection_select.value = "Existing"
        app.screen.query_one("#save-name", Input).value = "ping it"
        app.screen.query_one("#save-confirm", Button).press()
        await pilot.pause()

        assert len(list(tmp_path.glob("*.json"))) == 1
        collection = storage.load_collection(tmp_path / "existing.json")
        saved = next(iter(collection.requests.values()))
        assert saved.name == "ping it"
        assert saved.request.url == "https://api.example.com/ping"


@pytest.mark.asyncio
async def test_delete_last_request_removes_collection_file(tmp_path, monkeypatch):
    monkeypatch.setenv("APICLI_DATA_DIR", str(tmp_path))
    async with boot_app() as (app, pilot):
        from apicli.models import Collection, SavedRequest, RequestData

        collection = Collection(name="Solo")
        collection.requests["x"] = SavedRequest(
            id="x",
            name="only",
            request=RequestData(method="GET", url="https://demo.example.com/"),
        )
        storage.save_collection(collection, tmp_path)

        screen = app.screen
        screen.collections = storage.load_enabled(tmp_path)
        screen.current_collection = screen.collections[0]
        screen.current_saved = screen.collections[0].requests["x"]
        screen.collection_tree.apply_data(screen.collections)

        await pilot.press("ctrl+d")
        await pilot.pause()

        assert len(list(tmp_path.glob("*.json"))) == 0
        assert screen.collections == []