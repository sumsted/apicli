"""Pydantic request payloads for the web API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class SendPayload(BaseModel):
    request: dict[str, Any]


class CollectionCreate(BaseModel):
    name: str


class SaveRequestPayload(BaseModel):
    name: str
    request: dict[str, Any]


class ExportPayload(BaseModel):
    name: str
    request: dict[str, Any]
    response: dict[str, Any]


class SharePayload(BaseModel):
    name: str
    request: dict[str, Any]
