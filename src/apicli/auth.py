"""Authentication providers: basic auth and OAuth2 client-credentials flow."""

from __future__ import annotations

import time

import httpx

from .models import (
    OAuth2ClientCredentialsConfig,
    OAuth2Token,
)

SAFETY_MARGIN = 30


class OAuth2Provider:
    """Fetch and cache an OAuth2 access token using the client-credentials grant."""

    def __init__(self, config: OAuth2ClientCredentialsConfig):
        self.config = config
        self._token: OAuth2Token | None = None

    @property
    def cached_token(self) -> OAuth2Token | None:
        return self._token

    def is_valid(self) -> bool:
        token = self._token
        if token is None or not token.access_token:
            return False
        if token.expires_at and time.time() >= token.expires_at:
            return False
        return True

    def clear(self) -> None:
        self._token = None

    async def get_token(self, client: httpx.AsyncClient) -> OAuth2Token:
        if self.is_valid():
            assert self._token is not None
            return self._token

        config = self.config
        data: dict[str, str] = {"grant_type": "client_credentials"}
        if config.scope:
            data["scope"] = config.scope

        kwargs: dict = {"data": data}
        if config.include_client_credentials_in_body:
            data["client_id"] = config.client_id
            data["client_secret"] = config.client_secret
        else:
            kwargs["auth"] = (config.client_id, config.client_secret)

        response = await client.post(config.token_url, **kwargs)
        payload = _parse_token_payload(response)

        expires_in = payload.get("expires_in")
        expires_at = time.time() + float(expires_in) - SAFETY_MARGIN if expires_in else 0.0

        token = OAuth2Token(
            access_token=str(payload["access_token"]),
            token_type=str(payload.get("token_type") or config.token_type),
            expires_at=expires_at,
        )
        self._token = token
        return token

    def authorization_value(self, token: OAuth2Token) -> str:
        token_type = token.token_type.lower()
        if token_type in {"bearer", ""}:
            return f"Bearer {token.access_token}"
        if token_type == "basic":
            return f"Basic {token.access_token}"
        return f"{token.token_type} {token.access_token}"


def _parse_token_payload(response: httpx.Response) -> dict:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise AuthError(
            f"Token endpoint returned {response.status_code}: "
            f"{response.text[:300]}"
        ) from exc
    try:
        payload = response.json()
    except ValueError as exc:
        raise AuthError("Token endpoint did not return JSON.") from exc
    if not isinstance(payload, dict) or "access_token" not in payload:
        raise AuthError("Token endpoint response is missing 'access_token'.")
    return payload


class AuthError(Exception):
    pass