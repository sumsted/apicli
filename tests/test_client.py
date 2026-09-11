"""Tests for the HTTP execution layer (TLS verification toggles)."""

from __future__ import annotations

import ssl

import httpx
import pytest

from apicli import client
from apicli.client import _cert_error_hint, _client_kwargs, send_request
from apicli.models import RequestData


def test_client_kwargs_verify_default():
    kwargs = _client_kwargs(RequestData(method="GET", url="https://x"))
    assert "verify" not in kwargs


def test_client_kwargs_verify_disabled():
    request = RequestData(method="GET", url="https://x", verify_tls=False)
    kwargs = _client_kwargs(request)
    assert kwargs["verify"] is False


def test_client_kwargs_passes_transport():
    transport = httpx.AsyncBaseTransport()
    kwargs = _client_kwargs(RequestData(), transport=transport)
    assert kwargs["transport"] is transport


def test_client_kwargs_timeout_default():
    kwargs = _client_kwargs(RequestData())
    assert kwargs["timeout"] == client.DEFAULT_TIMEOUT


def test_cert_error_hint_matches_verification_failures():
    cause = Exception("CERTIFICATE_VERIFY_FAILED certificate verify failed: unable to get local issuer certificate")
    exc = httpx.ConnectError("connection error", request=httpx.Request("GET", "https://x"))
    exc.__cause__ = cause
    hint = _cert_error_hint(exc)
    assert "Skip TLS certificate verification" in hint
    plain = httpx.ConnectError("connection refused", request=httpx.Request("GET", "https://x"))
    assert _cert_error_hint(plain) == ""


@pytest.mark.asyncio
async def test_send_request_with_verify_disabled():
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json={"ok": True}))
    result = await send_request(
        RequestData(method="GET", url="https://x/", verify_tls=False),
        transport=transport,
    )
    assert result.ok
    assert result.status_code == 200