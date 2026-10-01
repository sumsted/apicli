"""Share and import request definitions as portable JSON files."""

from __future__ import annotations

import datetime
import json
from pathlib import Path

from .export import slugify
from .models import RequestData

FORMAT = "apicli-request"
FORMAT_VERSION = 1


def export_request_json(
    request: RequestData,
    name: str,
    data_dir: str | Path,
    timestamp: datetime.datetime | None = None,
) -> Path:
    """Write the request definition to ``{data_dir}/exports/`` and return the path.

    The filename is ``{slugified request name}-{YYYYmmdd-HHMMSS}.json``.
    """
    dest_dir = Path(data_dir) / "exports"
    dest_dir.mkdir(parents=True, exist_ok=True)
    if timestamp is None:
        timestamp = datetime.datetime.now()
    filename = f"{slugify(name)}-{timestamp:%Y%m%d-%H%M%S}.json"
    dest = dest_dir / filename
    dest.write_text(
        json.dumps(request_payload(request, name, timestamp), indent=2, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    return dest


def request_payload(
    request: RequestData,
    name: str,
    timestamp: datetime.datetime | None = None,
) -> dict:
    """Build the portable request JSON payload (without touching the disk)."""
    if timestamp is None:
        timestamp = datetime.datetime.now()
    return {
        "format": FORMAT,
        "version": FORMAT_VERSION,
        "exported_at": timestamp.isoformat(timespec="seconds"),
        "name": name,
        "request": request.to_dict(),
    }


def parse_request_json(raw: object, fallback_name: str = "") -> tuple[str, RequestData]:
    """Parse a shared request file (wrapper or bare request) into ``(name, request)``."""
    if not isinstance(raw, dict):
        raise ValueError("Not a valid apicli request file.")
    if isinstance(raw.get("request"), dict):
        name = str(raw.get("name", "")).strip() or fallback_name
        return name, RequestData.from_dict(raw["request"])
    if "method" in raw or "url" in raw:
        return fallback_name, RequestData.from_dict(raw)
    raise ValueError("Not a valid apicli request file.")


def load_request_json(path: str | Path) -> tuple[str, RequestData]:
    """Read a shared request JSON file, accepting either the apicli wrapper
    format or a bare ``RequestData`` dict. Returns ``(name, request)``."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return parse_request_json(raw, Path(path).stem)