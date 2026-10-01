"""Tests for the FastAPI web interface."""

from __future__ import annotations

import re
from contextlib import asynccontextmanager

import httpx
import pytest

from apicli import storage
from apicli.models import (
    AuthConfig,
    Collection,
    OAuth2ClientCredentialsConfig,
    RequestData,
    ResponseData,
    TimelineEvent,
)
from apicli.server import routes
from apicli.server.app import create_app


@asynccontextmanager
async def api_client(token: str | None = None):
    app = create_app(token=token)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


def _request_payload(method: str = "GET", url: str = "https://api.example.com/ping"):
    return RequestData(method=method, url=url).to_dict()


@pytest.mark.asyncio
async def test_health_and_empty_collections(tmp_path, monkeypatch):
    monkeypatch.setenv("APICLI_DATA_DIR", str(tmp_path))
    async with api_client() as client:
        health = await client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"

        collections = await client.get("/api/collections")
        assert collections.status_code == 200
        assert collections.json() == []


@pytest.mark.asyncio
async def test_collection_lifecycle(tmp_path, monkeypatch):
    monkeypatch.setenv("APICLI_DATA_DIR", str(tmp_path))
    async with api_client() as client:
        created = await client.post("/api/collections", json={"name": "Demo API"})
        assert created.status_code == 201
        assert created.json() == {"name": "Demo API", "requests": []}
        assert (tmp_path / "demo-api.json").exists()

        # Duplicate name is rejected.
        again = await client.post("/api/collections", json={"name": "Demo API"})
        assert again.status_code == 409

        listing = await client.get("/api/collections")
        assert listing.json() == [{"name": "Demo API", "request_count": 0}]

        fetched = await client.get("/api/collections/Demo API")
        assert fetched.status_code == 200

        deleted = await client.delete("/api/collections/Demo API")
        assert deleted.status_code == 204
        assert not (tmp_path / "demo-api.json").exists()
        assert (await client.get("/api/collections/Demo API")).status_code == 404


@pytest.mark.asyncio
async def test_request_crud(tmp_path, monkeypatch):
    monkeypatch.setenv("APICLI_DATA_DIR", str(tmp_path))
    storage.save_collection(Collection(name="Users API"), tmp_path)

    async with api_client() as client:
        created = await client.post(
            "/api/collections/Users API/requests",
            json={"name": "list users", "request": _request_payload()},
        )
        assert created.status_code == 201
        body = created.json()
        assert body["name"] == "list users"
        request_id = body["id"]

        fetched = await client.get(f"/api/collections/Users API/requests/{request_id}")
        assert fetched.status_code == 200
        assert fetched.json()["request"]["url"] == "https://api.example.com/ping"

        updated_payload = _request_payload("POST", "https://api.example.com/users")
        updated = await client.put(
            f"/api/collections/Users API/requests/{request_id}",
            json={"name": "create user", "request": updated_payload},
        )
        assert updated.status_code == 200
        assert updated.json()["name"] == "create user"

        # Persisted to disk.
        reloaded = storage.load_collection(tmp_path / "users-api.json")
        saved = reloaded.requests[request_id]
        assert saved.name == "create user"
        assert saved.request.method == "POST"

        deleted = await client.delete(
            f"/api/collections/Users API/requests/{request_id}"
        )
        assert deleted.status_code == 204
        # Last request removed -> collection file is gone.
        assert not (tmp_path / "users-api.json").exists()


@pytest.mark.asyncio
async def test_send_serializes_response(tmp_path, monkeypatch):
    monkeypatch.setenv("APICLI_DATA_DIR", str(tmp_path))

    async def fake_send(request, oauth_provider=None, timeout=60.0):
        return ResponseData(
            status_code=201,
            reason="Created",
            http_version="HTTP/1.1",
            headers=[("content-type", "application/json")],
            body=b'{"id": 7}',
            ok=True,
            elapsed_ms=12,
            size_bytes=8,
            url=request.url,
            request_method=request.method,
            sent_headers=[("Content-Type", "application/json")],
            sent_body=b'{"name": "kim"}',
            timeline=[TimelineEvent("request sent", 1), TimelineEvent("complete", 12)],
        )

    monkeypatch.setattr(routes, "send_request", fake_send)

    async with api_client() as client:
        response = await client.post(
            "/api/send",
            json={
                "request": _request_payload(
                    "POST", "https://api.example.com/users"
                )
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status_code"] == 201
        assert data["ok"] is True
        assert data["body"] == '{"id": 7}'
        assert data["sent_body"] == '{"name": "kim"}'
        assert data["headers"] == [["content-type", "application/json"]]
        assert data["timeline"] == [
            {"label": "request sent", "elapsed_ms": 1},
            {"label": "complete", "elapsed_ms": 12},
        ]


@pytest.mark.asyncio
async def test_send_uses_oauth_provider_when_configured(tmp_path, monkeypatch):
    monkeypatch.setenv("APICLI_DATA_DIR", str(tmp_path))
    seen = {}

    async def fake_send(request, oauth_provider=None, timeout=60.0):
        seen["provider"] = oauth_provider
        return ResponseData(status_code=200, ok=True)

    monkeypatch.setattr(routes, "send_request", fake_send)

    payload = RequestData(
        method="GET",
        url="https://api.example.com/secure",
        auth=AuthConfig(
            type="oauth2",
            oauth2=OAuth2ClientCredentialsConfig(
                token_url="https://auth.example.com/token",
                client_id="id",
                client_secret="secret",
            ),
        ),
    ).to_dict()

    async with api_client() as client:
        response = await client.post("/api/send", json={"request": payload})
        assert response.status_code == 200
        assert seen["provider"] is not None


@pytest.mark.asyncio
async def test_token_middleware(tmp_path, monkeypatch):
    monkeypatch.setenv("APICLI_DATA_DIR", str(tmp_path))
    async with api_client(token="s3cret") as client:
        unauthorized = await client.get("/api/collections")
        assert unauthorized.status_code == 401

        authorized = await client.get(
            "/api/collections", headers={"Authorization": "Bearer s3cret"}
        )
        assert authorized.status_code == 200


def _response_payload():
    return {
        "status_code": 200,
        "reason": "OK",
        "http_version": "HTTP/1.1",
        "headers": [["content-type", "application/json"]],
        "body": '{"ok": true}',
        "elapsed_ms": 5,
        "size_bytes": 12,
        "ok": True,
        "url": "https://api.example.com/ping",
        "request_method": "GET",
        "error": "",
        "timeline": [{"label": "complete", "elapsed_ms": 5}],
        "sent_headers": [],
        "sent_body": None,
    }


@pytest.mark.asyncio
async def test_export_returns_report(tmp_path, monkeypatch):
    monkeypatch.setenv("APICLI_DATA_DIR", str(tmp_path))
    async with api_client() as client:
        response = await client.post(
            "/api/export",
            json={
                "name": "Get Ping",
                "request": _request_payload(),
                "response": _response_payload(),
            },
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")
        assert re.search(
            r'Get-Ping-\d{8}-\d{6}\.txt', response.headers["content-disposition"]
        )
        text = response.text
        assert "REQUEST" in text and "RESPONSE" in text
        assert "Status:  200 OK" in text


@pytest.mark.asyncio
async def test_share_returns_portable_json(tmp_path, monkeypatch):
    monkeypatch.setenv("APICLI_DATA_DIR", str(tmp_path))
    async with api_client() as client:
        response = await client.post(
            "/api/share",
            json={"name": "Get Ping", "request": _request_payload()},
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        assert re.search(
            r'Get-Ping-\d{8}-\d{6}\.json', response.headers["content-disposition"]
        )
        payload = response.json()
        assert payload["format"] == "apicli-request"
        assert payload["name"] == "Get Ping"
        assert payload["request"]["url"] == "https://api.example.com/ping"


@pytest.mark.asyncio
async def test_import_accepts_wrapper_and_bare_formats(tmp_path, monkeypatch):
    monkeypatch.setenv("APICLI_DATA_DIR", str(tmp_path))
    async with api_client() as client:
        wrapper = await client.post(
            "/api/import",
            json={
                "format": "apicli-request",
                "version": 1,
                "name": "Shared request",
                "request": _request_payload("POST", "https://api.example.com/x"),
            },
        )
        assert wrapper.status_code == 200
        assert wrapper.json()["name"] == "Shared request"
        assert wrapper.json()["request"]["method"] == "POST"

        bare = await client.post(
            "/api/import", json=_request_payload("DELETE", "https://api.example.com/y")
        )
        assert bare.status_code == 200
        assert bare.json()["name"] == "Imported request"
        assert bare.json()["request"]["method"] == "DELETE"

        invalid = await client.post("/api/import", json={"nonsense": True})
        assert invalid.status_code == 422
