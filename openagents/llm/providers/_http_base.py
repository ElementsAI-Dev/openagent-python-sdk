"""Shared httpx-based transport for LLM providers."""

from __future__ import annotations

from typing import Any

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore[assignment]

from openagents.llm.base import LLMClient


class HTTPProviderClient(LLMClient):
    """LLM client with a reusable AsyncClient-backed transport."""

    def __init__(self, *, timeout_ms: int) -> None:
        self.timeout_ms = timeout_ms
        self._http_client = None

    def _require_httpx(self):
        if httpx is None:
            raise RuntimeError(
                "httpx is required for HTTP-backed LLM providers. "
                "Install with: uv add httpx"
            )
        return httpx

    def _build_timeout(self, *, read_timeout_s: float | None = None):
        httpx_mod = self._require_httpx()
        timeout_s = max(self.timeout_ms, 1) / 1000
        read_s = read_timeout_s if read_timeout_s is not None else timeout_s
        return httpx_mod.Timeout(timeout_s, read=read_s, write=timeout_s, pool=timeout_s)

    async def _get_http_client(self):
        if self._http_client is not None:
            return self._http_client

        httpx_mod = self._require_httpx()
        self._http_client = httpx_mod.AsyncClient(
            timeout=self._build_timeout(),
            limits=httpx_mod.Limits(max_connections=100, max_keepalive_connections=20),
            http2=True,
        )
        return self._http_client

    async def _request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
        read_timeout_s: float | None = None,
    ):
        client = await self._get_http_client()
        return await client.request(
            method,
            url,
            headers=headers,
            json=json_body,
            timeout=self._build_timeout(read_timeout_s=read_timeout_s),
        )

    async def _stream(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
        read_timeout_s: float | None = None,
    ):
        client = await self._get_http_client()
        return client.stream(
            method,
            url,
            headers=headers,
            json=json_body,
            timeout=self._build_timeout(read_timeout_s=read_timeout_s),
        )

    async def aclose(self) -> None:
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None
