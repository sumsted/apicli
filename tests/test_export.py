"""Unit tests for timeline capture and report export."""

from __future__ import annotations

import datetime

import httpx
import pytest

from apicli.client import send_request
from apicli.export import export_exchange
from apicli.models import RequestData, ResponseData, TimelineEvent


@pytest.mark.asyncio
async def test_send_request_records_timeline():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("x-test") == "yes"
        return httpx.Response(201, json={"created": True})

    request = RequestData(method="POST", url="https://example.com/api")
    request.body = '{"a": 1}'
    request.headers = [["x-test", "yes"]]

    result = await send_request(request, transport=httpx.MockTransport(handler))

    assert result.status_code == 201
    labels = [event.label for event in result.timeline]
    assert "request prepared" in labels
    assert "request sent" in labels
    assert "response status received" in labels
    assert "response body read" in labels
    assert "complete" in labels
    offsets = [event.elapsed_ms for event in result.timeline]
    assert offsets == sorted(offsets)
    assert ("x-test", "yes") in result.sent_headers
    assert result.sent_body == b'{"a": 1}'


@pytest.mark.asyncio
async def test_send_request_empty_url_timeline():
    result = await send_request(RequestData(url=""))
    assert result.error == "URL is empty."
    assert result.timeline[-1].label == "aborted: URL is empty"


def test_export_writes_report(tmp_path):
    request = RequestData(method="GET", url="https://api.example.com/users")
    response = ResponseData(
        status_code=200,
        reason="OK",
        http_version="HTTP/1.1",
        headers=[("content-type", "application/json")],
        body=b'{"users": 1}',
        elapsed_ms=123,
        size_bytes=12,
        ok=True,
        url=request.url,
        request_method=request.method,
        sent_headers=[("accept", "application/json")],
        sent_body=None,
        timeline=[
            TimelineEvent("request prepared", 0),
            TimelineEvent("request sent", 5),
            TimelineEvent("response status received", 120),
            TimelineEvent("response body read", 123),
            TimelineEvent("complete", 123),
        ],
    )

    timestamp = datetime.datetime(2026, 9, 4, 15, 30, 45)
    path = export_exchange(request, response, "Get Users", tmp_path, timestamp=timestamp)

    assert path.name == "Get-Users-20260904-153045.txt"
    text = path.read_text(encoding="utf-8")
    assert "Get Users" in text
    assert "GET" in text
    assert "https://api.example.com/users" in text
    assert "200 OK" in text
    assert "accept: application/json" in text
    assert "TIMELINE" in text
    assert "request prepared" in text
    assert "complete" in text


def test_export_pretty_prints_json_bodies(tmp_path):
    compact = b'{"users":[{"id":1,"name":"a"},{"id":2,"name":"b"}],"total":2}'
    request = RequestData(method="POST", url="https://api.example.com/users")
    request.body = '{"name":"new user"}'
    response = ResponseData(
        status_code=200,
        reason="OK",
        http_version="HTTP/1.1",
        headers=[("content-type", "application/json")],
        body=compact,
        elapsed_ms=1,
        size_bytes=len(compact),
        ok=True,
        url=request.url,
        request_method=request.method,
        sent_headers=[("content-type", "application/json")],
        sent_body=request.body.encode(),
    )
    path = export_exchange(request, response, "Create Users", tmp_path)
    text = path.read_text(encoding="utf-8")

    sent = text.split("Sent body:")[1].split("RESPONSE")[0]
    resp = text.split("Response body:")[1].split("TIMELINE")[0]
    assert '    "name": "new user"' in sent
    assert '    "name": "a"' in resp
    assert '    "users": [' in resp
    assert '{"users":[{"id":1,"name":"a"}' not in resp


def test_export_redacts_authorization(tmp_path):
    request = RequestData(method="GET", url="https://api.example.com/secret")
    response = ResponseData(
        status_code=200,
        reason="OK",
        http_version="HTTP/1.1",
        body=b"ok",
        elapsed_ms=1,
        size_bytes=2,
        ok=True,
        url=request.url,
        request_method=request.method,
        sent_headers=[("Authorization", "Basic c2VjcmV0")],
    )
    timestamp = datetime.datetime(2026, 9, 4, 15, 30, 45)
    path = export_exchange(request, response, "Secret", tmp_path, timestamp=timestamp)
    text = path.read_text(encoding="utf-8")
    assert "***" in text
    assert "Basic c2VjcmV0" not in text