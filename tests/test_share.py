"""Unit tests for sharing and importing request definitions."""

from __future__ import annotations

import datetime
import json

import pytest

from apicli.models import RequestData
from apicli.share import export_request_json, load_request_json


def test_share_roundtrip(tmp_path):
    request = RequestData(method="POST", url="https://api.example.com/items")
    request.headers = [["x-api-key", "abc"]]
    request.body = '{"a": 1}'
    request.body_type = "json"

    timestamp = datetime.datetime(2026, 9, 4, 16, 0, 0)
    path = export_request_json(request, "Create Item", tmp_path, timestamp=timestamp)

    assert path.name == "Create-Item-20260904-160000.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["format"] == "apicli-request"
    assert payload["request"]["url"] == "https://api.example.com/items"

    name, loaded = load_request_json(path)
    assert name == "Create Item"
    assert loaded.method == "POST"
    assert loaded.url == request.url
    assert loaded.headers == [["x-api-key", "abc"]]
    assert loaded.body == '{"a": 1}'


def test_import_bare_request_dict(tmp_path):
    path = tmp_path / "bare.json"
    path.write_text(json.dumps({"method": "GET", "url": "https://x.test/y"}))
    name, loaded = load_request_json(path)
    assert name == "bare"
    assert loaded.method == "GET"
    assert loaded.url == "https://x.test/y"


def test_import_invalid_raises(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"hello": 1}))
    with pytest.raises(ValueError):
        load_request_json(path)