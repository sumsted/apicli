"""Export request/response exchanges (with timing timeline) as plain-text reports."""

from __future__ import annotations

import datetime
from pathlib import Path

from .models import RequestData, ResponseData

EXPORT_DIR = "exports"

MAX_BODY_CHARS = 100_000


def export_exchange(
    request: RequestData,
    response: ResponseData,
    name: str,
    data_dir: str | Path,
    timestamp: datetime.datetime | None = None,
) -> Path:
    """Write a report into ``{data_dir}/exports/`` and return the path written.

    The filename is ``{slugified request name}-{YYYYmmdd-HHMMSS}.txt``.
    """
    dest_dir = Path(data_dir) / EXPORT_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    if timestamp is None:
        timestamp = datetime.datetime.now()
    filename = f"{slugify(name)}-{timestamp:%Y%m%d-%H%M%S}.txt"
    dest = dest_dir / filename
    dest.write_text(_render(request, response, name, timestamp), encoding="utf-8")
    return dest


def _render(
    request: RequestData,
    response: ResponseData,
    name: str,
    timestamp: datetime.datetime,
) -> str:
    lines: list[str] = []
    lines.append(f"Request: {name}")
    lines.append(f"Exported: {timestamp.isoformat(sep=' ', timespec='seconds')}")
    lines.append("=" * 72)
    lines.append("")

    lines.append("REQUEST")
    lines.append("-" * 72)
    lines.append(f"Method:  {request.method or 'GET'}")
    lines.append(f"URL:     {request.url}")
    lines.append(f"Auth:    {request.auth.summary()}")
    lines.append(f"Body:    {request.body_type if request.body.strip() else '(none)'}")
    lines.append("")
    lines.append("Sent headers:")
    if response.sent_headers:
        for key, value in response.sent_headers:
            redacted = _redact(key, value)
            lines.append(f"  {key}: {redacted}")
    else:
        lines.append("  (none)")
    lines.append("")
    lines.append("Sent body:")
    if response.sent_body is None:
        lines.append("  (none)")
    else:
        lines.extend(_body_lines(response.sent_body))
    lines.append("")

    lines.append("RESPONSE")
    lines.append("-" * 72)
    if response.error:
        lines.append(f"Status:  ERROR  {response.error}")
    else:
        status_line = f"{response.status_code} {response.reason}".strip()
        lines.append(f"Status:  {status_line}")
        lines.append(f"HTTP:    {response.http_version}")
        lines.append(f"Size:    {response.size_bytes} B")
    lines.append("")
    if not response.error:
        lines.append("Response headers:")
        if response.headers:
            for key, value in response.headers:
                lines.append(f"  {key}: {value}")
        else:
            lines.append("  (none)")
        lines.append("")
        lines.append("Response body:")
        lines.extend(_body_lines(response.body))
        lines.append("")

    lines.append("TIMELINE")
    lines.append("-" * 72)
    if response.timeline:
        width = max(len(str(e.elapsed_ms)) for e in response.timeline)
        for event in response.timeline:
            lines.append(f"{event.elapsed_ms:>{width}} ms  {event.label}")
        total = response.timeline[-1].elapsed_ms
        lines.append(f"{'':>{width}}      total {total} ms")
    else:
        lines.append("  (no timeline captured)")
    lines.append("")
    return "\n".join(lines)


def _body_lines(data: bytes) -> list[str]:
    text = _pretty_json(_decode(data))
    if len(text) > MAX_BODY_CHARS:
        text = text[:MAX_BODY_CHARS]
        return [f"  {line}" for line in text.splitlines()] + [
            f"  ...(truncated at {MAX_BODY_CHARS} chars)"
        ]
    return [f"  {line}" for line in text.splitlines()]


def _pretty_json(text: str) -> str:
    import json

    stripped = text.lstrip()
    if not (stripped.startswith("{") or stripped.startswith("[")):
        return text
    try:
        parsed = json.loads(text)
    except (ValueError, TypeError):
        return text
    if not isinstance(parsed, (dict, list)):
        return text
    return json.dumps(parsed, indent=2, ensure_ascii=False)


def _decode(data: bytes) -> str:
    for enc in ("utf-8", "latin-1"):
        try:
            return data.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return repr(data)


def _redact(key: str, value: str) -> str:
    if key.lower() in ("authorization", "proxy-authorization"):
        return "***"
    return value


def slugify(name: str) -> str:
    keep = [c if c.isalnum() or c in "-_" else "-" for c in name.strip()]
    return "".join(keep).strip("-") or "request"