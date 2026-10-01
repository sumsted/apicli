"""REST routes exposing the apicli core (collections, requests, send)."""

from __future__ import annotations

import datetime
import json

from fastapi import APIRouter, Body, HTTPException, Response

from .. import storage
from ..auth import OAuth2Provider
from ..client import send_request
from ..export import render_exchange, slugify
from ..models import Collection, SavedRequest
from ..share import parse_request_json, request_payload
from .schemas import (
    CollectionCreate,
    ExportPayload,
    SaveRequestPayload,
    SendPayload,
    SharePayload,
)
from .serializers import (
    deserialize_request,
    deserialize_response,
    serialize_collection,
    serialize_collection_summary,
    serialize_response,
    serialize_saved_request,
)

router = APIRouter(prefix="/api")


def _data_dir():
    return storage.data_dir()


def _load_collection(name: str) -> Collection:
    for collection in storage.load_enabled(_data_dir()):
        if collection.name == name:
            return collection
    raise HTTPException(status_code=404, detail=f"Collection '{name}' not found.")


def _find_request(collection: Collection, request_id: str) -> SavedRequest:
    saved = collection.requests.get(request_id)
    if saved is None:
        raise HTTPException(status_code=404, detail=f"Request '{request_id}' not found.")
    return saved


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "data_dir": str(_data_dir())}


@router.get("/collections")
def list_collections() -> list[dict]:
    return [
        serialize_collection_summary(collection)
        for collection in storage.load_enabled(_data_dir())
    ]


@router.post("/collections", status_code=201)
def create_collection(payload: CollectionCreate) -> dict:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Collection name is required.")
    exists = any(c.name == name for c in storage.load_enabled(_data_dir()))
    if exists:
        raise HTTPException(
            status_code=409, detail=f"Collection '{name}' already exists."
        )
    collection = Collection(name=name)
    storage.save_collection(collection, _data_dir())
    return serialize_collection(collection)


@router.get("/collections/{name}")
def get_collection(name: str) -> dict:
    return serialize_collection(_load_collection(name))


@router.delete("/collections/{name}", status_code=204)
def delete_collection(name: str) -> None:
    collection = _load_collection(name)
    storage.delete_collection(collection.name, _data_dir())


@router.get("/collections/{name}/requests/{request_id}")
def get_request(name: str, request_id: str) -> dict:
    collection = _load_collection(name)
    return serialize_saved_request(_find_request(collection, request_id))


@router.post("/collections/{name}/requests", status_code=201)
def create_request(name: str, payload: SaveRequestPayload) -> dict:
    collection = _load_collection(name)
    saved = SavedRequest(
        name=payload.name.strip() or "Untitled request",
        request=deserialize_request(payload.request),
    )
    collection.requests[saved.id] = saved
    storage.save_collection(collection, _data_dir())
    return serialize_saved_request(saved)


@router.put("/collections/{name}/requests/{request_id}")
def update_request(name: str, request_id: str, payload: SaveRequestPayload) -> dict:
    collection = _load_collection(name)
    saved = _find_request(collection, request_id)
    saved.name = payload.name.strip() or saved.name
    saved.request = deserialize_request(payload.request)
    storage.save_collection(collection, _data_dir())
    return serialize_saved_request(saved)


@router.delete("/collections/{name}/requests/{request_id}", status_code=204)
def delete_request(name: str, request_id: str) -> None:
    collection = _load_collection(name)
    if collection.requests.pop(request_id, None) is None:
        raise HTTPException(
            status_code=404, detail=f"Request '{request_id}' not found."
        )
    if collection.requests:
        storage.save_collection(collection, _data_dir())
    else:
        storage.delete_collection(collection.name, _data_dir())


@router.post("/import")
def import_request(payload: dict = Body(...)) -> dict:
    try:
        name, request = parse_request_json(payload, "Imported request")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"name": name, "request": request.to_dict()}


@router.post("/export")
def export_report(payload: ExportPayload) -> Response:
    request = deserialize_request(payload.request)
    response = deserialize_response(payload.response)
    timestamp = datetime.datetime.now()
    report = render_exchange(request, response, payload.name, timestamp)
    filename = f"{slugify(payload.name)}-{timestamp:%Y%m%d-%H%M%S}.txt"
    return Response(
        content=report,
        media_type="text/plain; charset=utf-8",
        headers={"content-disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/share")
def share_request(payload: SharePayload) -> Response:
    request = deserialize_request(payload.request)
    timestamp = datetime.datetime.now()
    body = json.dumps(
        request_payload(request, payload.name, timestamp), indent=2, ensure_ascii=False
    ) + "\n"
    filename = f"{slugify(payload.name)}-{timestamp:%Y%m%d-%H%M%S}.json"
    return Response(
        content=body,
        media_type="application/json",
        headers={"content-disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/send")
async def send(payload: SendPayload) -> dict:
    request = deserialize_request(payload.request)
    provider = (
        OAuth2Provider(request.auth.oauth2) if request.auth.type == "oauth2" else None
    )
    response = await send_request(request, oauth_provider=provider)
    return serialize_response(response)
