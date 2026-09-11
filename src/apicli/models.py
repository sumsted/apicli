"""Data models for API requests, auth, collections, and responses."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

HTTP_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]

AUTH_TYPES = ["none", "basic", "oauth2"]

BODY_TYPES = ["json", "xml", "form", "text"]


def new_id() -> str:
    return uuid.uuid4().hex


@dataclass
class BasicAuthConfig:
    username: str = ""
    password: str = ""


@dataclass
class OAuth2ClientCredentialsConfig:
    token_url: str = ""
    client_id: str = ""
    client_secret: str = ""
    scope: str = ""
    include_client_credentials_in_body: bool = True
    token_type: str = "Bearer"


@dataclass
class AuthConfig:
    type: str = "none"
    basic: BasicAuthConfig = field(default_factory=BasicAuthConfig)
    oauth2: OAuth2ClientCredentialsConfig = field(
        default_factory=OAuth2ClientCredentialsConfig
    )

    def summary(self) -> str:
        if self.type == "basic":
            user = self.basic.username or "?"
            return f"Basic ({user})"
        if self.type == "oauth2":
            return "OAuth2 (client-credentials)"
        return "No Auth"


@dataclass
class RequestData:
    method: str = "GET"
    url: str = ""
    headers: list[list[str]] = field(default_factory=list)
    body_type: str = "json"
    body: str = ""
    auth: AuthConfig = field(default_factory=AuthConfig)
    verify_tls: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "url": self.url,
            "headers": [[k, v] for k, v in self.headers],
            "body_type": self.body_type,
            "body": self.body,
            "verify_tls": self.verify_tls,
            "auth": {
                "type": self.auth.type,
                "basic": {
                    "username": self.auth.basic.username,
                    "password": self.auth.basic.password,
                },
                "oauth2": {
                    "token_url": self.auth.oauth2.token_url,
                    "client_id": self.auth.oauth2.client_id,
                    "client_secret": self.auth.oauth2.client_secret,
                    "scope": self.auth.oauth2.scope,
                    "include_client_credentials_in_body": (
                        self.auth.oauth2.include_client_credentials_in_body
                    ),
                    "token_type": self.auth.oauth2.token_type,
                },
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RequestData":
        auth = data.get("auth") or {}
        basic = auth.get("basic") or {}
        oauth2 = auth.get("oauth2") or {}
        return cls(
            method=data.get("method", "GET"),
            url=data.get("url", ""),
            headers=[[str(k), str(v)] for k, v in data.get("headers", [])],
            body_type=data.get("body_type", "json"),
            body=data.get("body", ""),
            verify_tls=bool(data.get("verify_tls", True)),
            auth=AuthConfig(
                type=auth.get("type", "none"),
                basic=BasicAuthConfig(
                    username=basic.get("username", ""),
                    password=basic.get("password", ""),
                ),
                oauth2=OAuth2ClientCredentialsConfig(
                    token_url=oauth2.get("token_url", ""),
                    client_id=oauth2.get("client_id", ""),
                    client_secret=oauth2.get("client_secret", ""),
                    scope=oauth2.get("scope", ""),
                    include_client_credentials_in_body=oauth2.get(
                        "include_client_credentials_in_body", True
                    ),
                    token_type=oauth2.get("token_type", "Bearer"),
                ),
            ),
        )


@dataclass
class SavedRequest:
    id: str = field(default_factory=new_id)
    name: str = "Untitled request"
    request: RequestData = field(default_factory=RequestData)

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "request": self.request.to_dict()}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SavedRequest":
        return cls(
            id=data.get("id") or new_id(),
            name=data.get("name", "Untitled request"),
            request=RequestData.from_dict(data.get("request") or {}),
        )


@dataclass
class Collection:
    name: str = "Untitled collection"
    requests: dict[str, SavedRequest] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "requests": [r.to_dict() for r in self.requests.values()],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Collection":
        return cls(
            name=data.get("name", "Untitled collection"),
            requests={
                r.id: r
                for r in (SavedRequest.from_dict(x) for x in data.get("requests", []))
            },
        )


@dataclass
class TimelineEvent:
    """One timed milestone in the request/response lifecycle."""

    label: str
    elapsed_ms: int


@dataclass
class ResponseData:
    status_code: int = 0
    reason: str = ""
    http_version: str = ""
    headers: list[tuple[str, str]] = field(default_factory=list)
    body: bytes = b""
    elapsed_ms: int = 0
    size_bytes: int = 0
    ok: bool = False
    url: str = ""
    request_method: str = ""
    error: str = ""
    timeline: list[TimelineEvent] = field(default_factory=list)
    sent_headers: list[tuple[str, str]] = field(default_factory=list)
    sent_body: bytes | None = None

    @property
    def text(self) -> str:
        if self.error:
            return self.error
        for enc in ("utf-8", "latin-1"):
            try:
                return self.body.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue
        return repr(self.body)


@dataclass
class OAuth2Token:
    access_token: str
    token_type: str = "Bearer"
    expires_at: float = 0.0