"""HTTP client for the TrainingPeaks Strength API.

Strength workouts live on a separate API namespace from the rest of TP.
This module targets `https://api.peakswaresb.com/rx/activity/v1/`.

The Bearer token from the standard TPClient OAuth flow works on this
domain too, so we share the token cache and only swap the base URL.
"""

from __future__ import annotations

import asyncio
import json as _json
import logging
import time
from typing import Any

import httpx

from tp_mcp.client.http import (
    DEFAULT_TIMEOUT,
    MIN_REQUEST_INTERVAL,
    APIResponse,
    ErrorCode,
    TPClient,
)

logger = logging.getLogger("tp-mcp.strength")

STRENGTH_API_BASE = "https://api.peakswaresb.com"
STRENGTH_PREFIX = "/rx/activity/v1"


class StrengthClient:
    """Async HTTP client for the TrainingPeaks Strength API.

    Reuses the standard `TPClient._shared_token_cache` for OAuth, so authentication
    is unified across both API namespaces.
    """

    def __init__(self, timeout: float = DEFAULT_TIMEOUT):
        self.base_url = STRENGTH_API_BASE
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None
        self._last_request_time: float = 0.0
        # Reuse the standard TPClient token cache. This means a token refresh
        # triggered by either client benefits the other.
        self._token_cache = TPClient._get_token_cache()
        # Hold a TPClient instance so we can reuse its token-refresh logic.
        # We don't open its httpx client; we only call _ensure_access_token().
        self._tp_client = TPClient(timeout=timeout)

    async def __aenter__(self) -> StrengthClient:
        await self._ensure_client()
        # The wrapped TPClient also needs its own httpx client to perform
        # the cookie-for-token exchange when the cache is stale.
        await self._tp_client._ensure_client()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def _ensure_client(self) -> None:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)

    async def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < MIN_REQUEST_INTERVAL:
            await asyncio.sleep(MIN_REQUEST_INTERVAL - elapsed)
        self._last_request_time = time.monotonic()

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        await self._tp_client.close()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token_cache.access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        json: Any = None,
        params: dict[str, Any] | None = None,
        _retry_on_401: bool = True,
    ) -> APIResponse:
        """Authenticated request against the strength API."""
        await self._ensure_client()
        assert self._client is not None

        # Make sure we have a valid token (reuses the shared cache).
        token_result = await self._tp_client._ensure_access_token()
        if not token_result.success:
            return token_result

        await self._throttle()

        # Endpoints can be passed with or without the prefix.
        if endpoint.startswith("http"):
            url = endpoint
        elif endpoint.startswith("/"):
            url = f"{self.base_url}{endpoint}"
        else:
            url = f"{self.base_url}{STRENGTH_PREFIX}/{endpoint}"

        try:
            response = await self._client.request(
                method=method.upper(),
                url=url,
                headers=self._headers(),
                json=json,
                params=params,
            )
        except httpx.TimeoutException:
            return APIResponse(
                success=False,
                error_code=ErrorCode.NETWORK_ERROR,
                message=f"Request timed out: {method} {url}",
            )
        except httpx.RequestError as e:
            return APIResponse(
                success=False,
                error_code=ErrorCode.NETWORK_ERROR,
                message=f"Network error: {e}",
            )

        if response.status_code == 401 and _retry_on_401:
            # Cached token went bad mid-request. Clear and retry once.
            self._token_cache.clear()
            return await self._request(
                method, endpoint, json=json, params=params, _retry_on_401=False
            )

        if response.status_code == 404:
            return APIResponse(
                success=False,
                error_code=ErrorCode.NOT_FOUND,
                message=f"Resource not found: {endpoint}",
            )

        if response.status_code == 429:
            return APIResponse(
                success=False,
                error_code=ErrorCode.RATE_LIMITED,
                message="Rate limit exceeded. Back off and retry.",
            )

        # Some endpoints (privateWorkoutNote) legitimately return 204 No Content.
        if response.status_code == 204:
            return APIResponse(success=True, data=None)

        if not (200 <= response.status_code < 300):
            try:
                err_text = response.text[:500]
            except Exception:
                err_text = "<unreadable>"
            return APIResponse(
                success=False,
                error_code=ErrorCode.API_ERROR,
                message=(
                    f"API error {response.status_code} on {method} {endpoint}: {err_text}"
                ),
            )

        # Success path.
        try:
            data = response.json() if response.text else None
        except _json.JSONDecodeError as e:
            return APIResponse(
                success=False,
                error_code=ErrorCode.API_ERROR,
                message=f"Invalid JSON in response: {e}",
            )

        return APIResponse(success=True, data=data)

    async def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> APIResponse:
        return await self._request("GET", endpoint, params=params)

    async def put(
        self,
        endpoint: str,
        json: Any = None,
    ) -> APIResponse:
        return await self._request("PUT", endpoint, json=json)

    async def post(
        self,
        endpoint: str,
        json: Any = None,
    ) -> APIResponse:
        return await self._request("POST", endpoint, json=json)

    async def delete(
        self,
        endpoint: str,
    ) -> APIResponse:
        return await self._request("DELETE", endpoint)
