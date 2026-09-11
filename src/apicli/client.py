"""HTTP execution layer built on httpx."""

from __future__ import annotations

import time

import httpx

from .auth import AuthError, OAuth2Provider
from .models import (
    BODY_TYPES,
    HTTP_METHODS,
    RequestData,
    ResponseData,
    TimelineEvent,
)

BODY_CONTENT_TYPES = {
    "json": "application/json",
    "xml": "application/xml",
    "form": "application/x-www-form-urlencoded",
    "text": "text/plain",
}

DEFAULT_TIMEOUT = 60.0


def _client_kwargs(
    request: RequestData,
    timeout: float = DEFAULT_TIMEOUT,
    transport: httpx.AsyncBaseTransport | None = None,
) -> dict:
    """Build httpx.AsyncClient kwargs from a RequestData (testable in isolation)."""
    kwargs: dict = {"timeout": timeout, "follow_redirects": True}
    if not request.verify_tls:
        kwargs["verify"] = False
    if transport is not None:
        kwargs["transport"] = transport
    return kwargs


def _cert_error_hint(exc: Exception) -> str:
    cause = exc.__cause__ if exc.__cause__ else exc
    if isinstance(cause, Exception) and "certificate verify failed" in str(cause).lower():
        return (
            " (TLS certificate verification failed -- tick the "
            "'Skip TLS certificate verification' option in the Auth tab)"
        )
    return ""


async def send_request(
    request: RequestData,
    oauth_provider: OAuth2Provider | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    transport: httpx.AsyncBaseTransport | None = None,
) -> ResponseData:
    """Execute a RequestData and return a ResponseData, never raising on network errors.

    ``transport`` is passed straight through to ``httpx.AsyncClient`` (used in tests).
    A timeline of milestones is captured on ``result.timeline`` on every code path.
    """
    method = (request.method or "GET").upper()
    url = (request.url or "").strip()
    result = ResponseData(request_method=method, url=url)

    started = time.perf_counter()

    def mark(label: str) -> None:
        result.timeline.append(
            TimelineEvent(label, int((time.perf_counter() - started) * 1000))
        )

    mark("request prepared")
    if not url:
        result.error = "URL is empty."
        mark("aborted: URL is empty")
        return result
    if method not in HTTP_METHODS:
        result.error = f"Unsupported method: {method}"
        mark("aborted: unsupported method")
        return result

    headers = _build_headers(request)
    content = _build_content(request, headers)

    try:
        client_kwargs = _client_kwargs(request, timeout, transport)
        async with httpx.AsyncClient(**client_kwargs) as client:
            await _apply_auth(client, request, headers, oauth_provider, result)
            mark("auth configured")
            if result.error:
                mark("aborted: auth failed")
                return result

            result.sent_headers = list(headers.items())
            result.sent_body = content

            mark("request sent")
            response = await client.request(
                method,
                url,
                headers=headers,
                content=content,
            )
            elapsed_s = time.perf_counter() - started
            mark("response status received")
            body = await response.aread()
            mark("response body read")

            result.status_code = response.status_code
            result.reason = response.reason_phrase or ""
            result.http_version = response.http_version
            result.headers = [(k, v) for k, v in response.headers.multi_items()]
            result.body = body
            result.elapsed_ms = int(elapsed_s * 1000)
            result.size_bytes = len(body)
            result.ok = 300 > response.status_code >= 200
            mark("complete")
            return result
    except httpx.TimeoutException:
        result.error = "Request timed out."
        mark("failed: timeout")
        return result
    except httpx.TransportError as exc:
        result.error = f"Connection error: {exc}{_cert_error_hint(exc)}"
        mark("failed: connection error")
        return result
    except AuthError as exc:
        result.error = f"Auth error: {exc}"
        mark("failed: auth error")
        return result
    except Exception as exc:  # pragma: no cover - defensive
        result.error = f"Unexpected error: {exc}"
        mark("failed: unexpected error")
        return result


async def _apply_auth(
    client: httpx.AsyncClient,
    request: RequestData,
    headers: dict[str, str],
    oauth_provider: OAuth2Provider | None,
    result: ResponseData,
) -> None:
    auth = request.auth
    if auth.type == "basic":
        if not auth.basic.username and not auth.basic.password:
            result.error = "Basic auth requires a username and password."
            return
        headers["Authorization"] = _basic_header(
            auth.basic.username, auth.basic.password
        )
    elif auth.type == "oauth2":
        if oauth_provider is None:
            result.error = "OAuth2 configured but no token provider is available."
            return
        token = await oauth_provider.get_token(client)
        headers["Authorization"] = oauth_provider.authorization_value(token)


def _basic_header(username: str, password: str) -> str:
    import base64

    raw = f"{username}:{password}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def _build_headers(request: RequestData) -> dict[str, str]:
    headers: dict[str, str] = {}
    for key, value in request.headers:
        key = (key or "").strip()
        value = (value or "").strip()
        if key:
            headers[key] = value
    return headers


def _build_content(request: RequestData, headers: dict[str, str]) -> bytes | None:
    if request.method in ("GET", "HEAD", "OPTIONS") or not request.body.strip():
        return None
    body_type = request.body_type if request.body_type in BODY_TYPES else "text"
    headers.setdefault("Content-Type", BODY_CONTENT_TYPES[body_type])
    return request.body.encode("utf-8")