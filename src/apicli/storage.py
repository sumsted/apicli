"""JSON persistence for collections and app settings."""

from __future__ import annotations

import json
import os
from pathlib import Path

from .models import Collection, SavedRequest, RequestData

DEFAULT_DATA_DIR = Path("data")

DATA_DIR_ENV = "APICLI_DATA_DIR"


def data_dir() -> Path:
    """The directory for collection JSON files (override with $APICLI_DATA_DIR)."""
    override = os.environ.get(DATA_DIR_ENV)
    return Path(override).expanduser() if override else DEFAULT_DATA_DIR


def load_enabled(data_dir: str | Path = DEFAULT_DATA_DIR) -> list[Collection]:
    """Load all collection JSON files from a directory, sorted by name."""
    path = Path(data_dir)
    if not path.is_dir():
        return []
    collections: list[Collection] = []
    for file in sorted(path.glob("*.json")):
        if file.name == "settings.json":
            continue
        try:
            collections.append(load_collection(file))
        except (OSError, ValueError):
            continue
    return collections


def load_collection(path: str | Path) -> Collection:
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        legacy = {"name": path.stem, "requests": data}
        return Collection.from_dict(legacy)
    return Collection.from_dict(data)


def save_collection(collection: Collection, data_dir: str | Path = DEFAULT_DATA_DIR) -> Path:
    """Save a collection as {slug}.json inside data_dir. Returns the path written."""
    path = Path(data_dir)
    path.mkdir(parents=True, exist_ok=True)
    slug = _slugify(collection.name)
    dest = path / f"{slug}.json"
    _write_json(dest, collection.to_dict())
    return dest


def delete_collection(name: str, data_dir: str | Path = DEFAULT_DATA_DIR) -> Path | None:
    path = Path(data_dir) / f"{_slugify(name)}.json"
    if path.exists():
        path.unlink()
        return path
    return None


def save_request(
    request: SavedRequest, collection: Collection, data_dir: str | Path = DEFAULT_DATA_DIR
) -> Path:
    return save_collection(collection, data_dir)


def _slugify(name: str) -> str:
    keep = [c if c.isalnum() or c in "-_" else "-" for c in name.strip()]
    slug = "".join(keep).strip("-").lower()
    return slug or "collection"


def _write_json(path: Path, data: object) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)