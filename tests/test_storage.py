"""Tests for JSON persistence and model round-trips."""

from __future__ import annotations

import json

from apicli.models import (
    AuthConfig,
    BasicAuthConfig,
    Collection,
    OAuth2ClientCredentialsConfig,
    RequestData,
    SavedRequest,
)
from apicli import storage


def test_model_round_trip():
    request = RequestData(
        method="POST",
        url="https://example.com/api",
        headers=[["X-Token", "abc"], ["Content-Type", "application/json"]],
        body_type="json",
        body='{"a": 1}',
        auth=AuthConfig(
            type="oauth2",
            oauth2=OAuth2ClientCredentialsConfig(
                token_url="https://idp/token",
                client_id="cid",
                client_secret="csec",
                scope="scope-a",
            ),
        ),
    )
    restored = RequestData.from_dict(request.to_dict())
    assert restored.method == "POST"
    assert restored.headers == [["X-Token", "abc"], ["Content-Type", "application/json"]]
    assert restored.auth.oauth2.client_id == "cid"
    assert restored.auth.oauth2.scope == "scope-a"


def test_collection_round_trip(tmp_path):
    collection = Collection(name="My Coll")
    request = SavedRequest(name="get users", request=RequestData(method="GET", url="https://x/u"))
    collection.requests[request.id] = request

    dest = storage.save_collection(collection, tmp_path)
    assert dest.exists()

    loaded = storage.load_collection(dest)
    assert loaded.name == "My Coll"
    assert request.id in loaded.requests
    assert loaded.requests[request.id].request.method == "GET"


def test_load_enabled_ignores_settings_and_garbage(tmp_path):
    (tmp_path / "settings.json").write_text("{}")
    (tmp_path / "broken.json").write_text("{not json")
    storage.save_collection(Collection(name="A"), tmp_path)
    storage.save_collection(Collection(name="B"), tmp_path)

    collections = storage.load_enabled(tmp_path)
    assert [c.name for c in collections] == ["A", "B"]


def test_slug_collision_uses_dash_fallback():
    assert storage._slugify("Hello World") == "hello-world"
    assert storage._slugify("!!!") == "collection"