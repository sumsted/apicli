"""Serialize core models into JSON-friendly payloads for the web API."""

from __future__ import annotations

from ..models import Collection, RequestData, ResponseData, SavedRequest, TimelineEvent

MAX_BODY_CHARS = 100_000


def _decode(data: bytes) -> str:
    for encoding in ("utf-8", "latin-1"):
        try:
            return data.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return repr(data)


def _truncate(text: str) -> str:
    if len(text) > MAX_BODY_CHARS:
        return text[:MAX_BODY_CHARS] + f"\n…(truncated at {MAX_BODY_CHARS} chars)"
    return text


def serialize_response(response: ResponseData) -> dict:
    """Convert a ResponseData (which holds raw bytes) into a JSON-safe dict."""
    return {
        "status_code": response.status_code,
        "reason": response.reason,
        "http_version": response.http_version,
        "headers": [[k, v] for k, v in response.headers],
        "body": _truncate(_decode(response.body)) if response.body else "",
        "elapsed_ms": response.elapsed_ms,
        "size_bytes": response.size_bytes,
        "ok": response.ok,
        "url": response.url,
        "request_method": response.request_method,
        "error": response.error,
        "timeline": [
            {"label": event.label, "elapsed_ms": event.elapsed_ms}
            for event in response.timeline
        ],
        "sent_headers": [[k, v] for k, v in response.sent_headers],
        "sent_body": (
            _decode(response.sent_body) if response.sent_body is not None else None
        ),
    }


def serialize_collection_summary(collection: Collection) -> dict:
    return {"name": collection.name, "request_count": len(collection.requests)}


def serialize_collection(collection: Collection) -> dict:
    return {
        "name": collection.name,
        "requests": [
            {"id": saved.id, "name": saved.name}
            for saved in collection.requests.values()
        ],
    }


def serialize_saved_request(saved: SavedRequest) -> dict:
    return {"id": saved.id, "name": saved.name, "request": saved.request.to_dict()}


def deserialize_request(payload: dict) -> RequestData:
    return RequestData.from_dict(payload)


def deserialize_response(payload: dict) -> ResponseData:
    """Rebuild a ResponseData from the JSON produced by ``serialize_response``."""
    sent_body = payload.get("sent_body")
    return ResponseData(
        status_code=int(payload.get("status_code", 0)),
        reason=payload.get("reason", ""),
        http_version=payload.get("http_version", ""),
        headers=[(str(k), str(v)) for k, v in payload.get("headers", [])],
        body=(payload.get("body") or "").encode("utf-8"),
        elapsed_ms=int(payload.get("elapsed_ms", 0)),
        size_bytes=int(payload.get("size_bytes", 0)),
        ok=bool(payload.get("ok", False)),
        url=payload.get("url", ""),
        request_method=payload.get("request_method", ""),
        error=payload.get("error", ""),
        timeline=[
            TimelineEvent(str(e.get("label", "")), int(e.get("elapsed_ms", 0)))
            for e in payload.get("timeline", [])
        ],
        sent_headers=[(str(k), str(v)) for k, v in payload.get("sent_headers", [])],
        sent_body=sent_body.encode("utf-8") if sent_body is not None else None,
    )
