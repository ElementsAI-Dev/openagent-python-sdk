from __future__ import annotations

import json
import types

import pytest

from openagents.llm.providers import _http_base as http_base_module
from openagents.llm.providers._http_base import HTTPProviderClient
from openagents.llm.providers.anthropic import AnthropicClient
from openagents.llm.providers.anthropic import _parse_tool_input as anthropic_parse_tool_input
from openagents.llm.providers.anthropic import _parse_usage as anthropic_parse_usage
from openagents.llm.providers.openai_compatible import (
    OpenAICompatibleClient,
    _extract_text_content,
    _parse_json_object,
    _parse_tool_calls,
)


class _FakeResponse:
    def __init__(self, *, status_code: int = 200, json_data: dict | None = None, records: list[bytes] | None = None):
        self.status_code = status_code
        self._json_data = json_data or {}
        self._records = records or []
        self.text = json.dumps(self._json_data)
        self.content = self.text.encode("utf-8")

    def json(self) -> dict:
        return self._json_data

    async def aread(self) -> bytes:
        return self.content

    async def aiter_bytes(self):
        for record in self._records:
            yield record

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


class _FakeAsyncClient:
    def __init__(self, *, response: _FakeResponse, stream_response: _FakeResponse | None = None, **kwargs):
        self.response = response
        self.stream_response = stream_response or _FakeResponse(records=[])
        self.kwargs = kwargs
        self.requests: list[dict] = []
        self.stream_requests: list[dict] = []
        self.closed = False

    async def request(self, method: str, url: str, **kwargs):
        self.requests.append({"method": method, "url": url, **kwargs})
        return self.response

    def stream(self, method: str, url: str, **kwargs):
        self.stream_requests.append({"method": method, "url": url, **kwargs})
        return self.stream_response

    async def aclose(self) -> None:
        self.closed = True


def _install_fake_httpx(
    monkeypatch, *, response: _FakeResponse, stream_response: _FakeResponse | None = None
) -> _FakeAsyncClient:
    fake_client = _FakeAsyncClient(response=response, stream_response=stream_response)
    fake_httpx = types.SimpleNamespace(
        Timeout=lambda *args, **kwargs: {"args": args, "kwargs": kwargs},
        Limits=lambda **kwargs: kwargs,
        AsyncClient=lambda **kwargs: fake_client,
    )
    monkeypatch.setattr(http_base_module, "httpx", fake_httpx)
    return fake_client


class _TransportHarness(HTTPProviderClient):
    def __init__(self):
        super().__init__(timeout_ms=2500)


@pytest.mark.asyncio
async def test_http_provider_client_builds_timeouts_caches_client_and_closes(monkeypatch):
    fake_client = _install_fake_httpx(monkeypatch, response=_FakeResponse(json_data={"ok": True}))
    client = _TransportHarness()

    timeout = client._build_timeout(read_timeout_s=9.0)
    first = await client._get_http_client()
    second = await client._get_http_client()
    await client._request("POST", "https://example.com", headers={"A": "1"}, json_body={"ok": True})
    stream_ctx = await client._stream("GET", "https://example.com/stream")
    await client.aclose()

    assert timeout["kwargs"]["read"] == 9.0
    assert first is second is fake_client
    assert fake_client.requests[0]["json"] == {"ok": True}
    assert stream_ctx is fake_client.stream_response
    assert fake_client.closed is True
    assert client._http_client is None

    monkeypatch.setattr(http_base_module, "httpx", None)
    with pytest.raises(RuntimeError, match="httpx is required"):
        client._require_httpx()


@pytest.mark.asyncio
async def test_anthropic_helpers_and_error_paths(monkeypatch):
    client = AnthropicClient(api_base="https://api.anthropic.com", model="claude-test")

    assert anthropic_parse_usage(None) is None
    assert anthropic_parse_usage({"input_tokens": 2, "output_tokens": 3}).total_tokens == 5
    parsed, raw = anthropic_parse_tool_input('{"path":"README.md"}')
    assert parsed == {"path": "README.md"}
    assert raw == '{"path":"README.md"}'
    assert anthropic_parse_tool_input("not-json") == ({}, "not-json")
    assert client._build_structured_output_tool({"type": "json"})[0] == "structured_output"
    assert client._build_structured_output_tool({"type": "other"}) == (None, None)
    assert client._parse_sse_event(b'event: ping\ndata: {"ok": true}\n') == ("ping", '{"ok": true}')
    assert client._parse_sse_event(b'{"choices": []}') == (None, '{"choices": []}')
    assert client._extract_stream_error({"error": {"message": "bad"}}) == "bad"
    assert "status" in client._extract_stream_error({"base_resp": {"status_code": 503}}).lower()

    _install_fake_httpx(monkeypatch, response=_FakeResponse(status_code=500, json_data={"error": "bad"}))
    with pytest.raises(RuntimeError, match="HTTP 500"):
        await client.generate(messages=[{"role": "user", "content": "hello"}])


@pytest.mark.asyncio
async def test_anthropic_complete_stream_handles_raw_choice_records_and_http_errors(monkeypatch):
    stream_response = _FakeResponse(
        records=[
            b'{"choices":[{"delta":{"content":"Hello"},"finish_reason":"end_turn"}],"usage":{"prompt_tokens":4,"completion_tokens":2,"total_tokens":6}}\n\n',
        ]
    )
    _install_fake_httpx(monkeypatch, response=_FakeResponse(json_data={}), stream_response=stream_response)
    client = AnthropicClient(api_base="https://api.anthropic.com", model="claude-test")

    chunks = [chunk async for chunk in client.complete_stream(messages=[{"role": "user", "content": "hello"}])]
    assert [chunk.type for chunk in chunks] == ["content_block_delta", "message_stop"]
    assert chunks[0].delta == {"type": "text_delta", "text": "Hello"}
    assert chunks[1].content == {"stop_reason": "end_turn"}

    error_stream = _FakeResponse(status_code=429, json_data={"error": "rate-limited"})
    _install_fake_httpx(monkeypatch, response=_FakeResponse(json_data={}), stream_response=error_stream)
    error_client = AnthropicClient(api_base="https://api.anthropic.com", model="claude-test")
    error_chunks = [
        chunk async for chunk in error_client.complete_stream(messages=[{"role": "user", "content": "hello"}])
    ]
    assert error_chunks[0].type == "error"
    assert "HTTP 429" in (error_chunks[0].error or "")


@pytest.mark.asyncio
async def test_openai_compatible_helpers_and_error_paths(monkeypatch):
    client = OpenAICompatibleClient(api_base="https://api.openai.com", model="gpt-test")

    assert client._chat_completions_endpoint() == "https://api.openai.com/v1/chat/completions"
    assert _extract_text_content("hello") == "hello"
    assert _extract_text_content([{"text": "a"}, {"text": "b"}, {"ignored": True}]) == "ab"
    assert _extract_text_content(123) == "123"
    assert _parse_json_object('{"x": 1}') == {"x": 1}
    assert _parse_json_object("bad-json") == {}
    assert _parse_tool_calls(
        [
            {"id": "call_1", "type": "function", "function": {"name": "read", "arguments": '{"path":"README.md"}'}},
            {"function": {"name": ""}},
        ]
    )[0].arguments == {"path": "README.md"}
    assert client._parse_sse_record(b"data: one\ndata: two\n") == "one\ntwo"

    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    assert client._build_headers()["Authorization"] == "Bearer secret"

    _install_fake_httpx(monkeypatch, response=_FakeResponse(status_code=500, json_data={"error": "bad"}))
    with pytest.raises(RuntimeError, match="HTTP 500"):
        await client.generate(messages=[{"role": "user", "content": "hello"}])


@pytest.mark.asyncio
async def test_openai_compatible_complete_stream_handles_http_errors_and_trailing_usage(monkeypatch):
    stream_response = _FakeResponse(
        records=[
            b'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n',
            b'data: {"choices":[{"finish_reason":"stop"}]}\n\n',
            b'data: {"choices":[],"usage":{"prompt_tokens":3,"completion_tokens":2,"total_tokens":5}}\n\n',
            b"data: [DONE]\n\n",
        ]
    )
    _install_fake_httpx(monkeypatch, response=_FakeResponse(json_data={}), stream_response=stream_response)
    client = OpenAICompatibleClient(api_base="https://api.openai.com/v1", model="gpt-test")

    chunks = [chunk async for chunk in client.complete_stream(messages=[{"role": "user", "content": "hello"}])]
    assert [chunk.type for chunk in chunks] == ["content_block_delta", "message_stop"]
    assert chunks[0].delta == {"type": "text_delta", "text": "Hello"}
    assert chunks[1].content == {"stop_reason": "stop"}
    assert chunks[1].usage.total_tokens == 5

    error_stream = _FakeResponse(status_code=401, json_data={"error": "unauthorized"})
    _install_fake_httpx(monkeypatch, response=_FakeResponse(json_data={}), stream_response=error_stream)
    error_client = OpenAICompatibleClient(api_base="https://api.openai.com/v1", model="gpt-test")
    error_chunks = [
        chunk async for chunk in error_client.complete_stream(messages=[{"role": "user", "content": "hello"}])
    ]
    assert error_chunks[0].type == "error"
    assert "HTTP 401" in (error_chunks[0].error or "")
