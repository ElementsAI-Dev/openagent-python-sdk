"""Base LLM client contracts and normalized response models."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, AsyncIterator


def _parse_structured_output(
    output_text: str,
    response_format: dict[str, Any] | None,
) -> Any:
    if not isinstance(response_format, dict):
        return None

    format_type = str(response_format.get("type", "")).strip().lower()
    if format_type not in {"json", "json_object", "json_schema"}:
        return None

    try:
        return json.loads(output_text)
    except (TypeError, json.JSONDecodeError):
        return None


@dataclass
class LLMUsage:
    """Normalized token usage for one LLM response."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def normalized(self) -> "LLMUsage":
        input_tokens = max(int(self.input_tokens), 0)
        output_tokens = max(int(self.output_tokens), 0)
        total_tokens = max(int(self.total_tokens or (input_tokens + output_tokens)), 0)
        return LLMUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            metadata=dict(self.metadata),
        )

    def merge(self, other: "LLMUsage | None") -> "LLMUsage":
        if other is None:
            return self.normalized()

        current = self.normalized()
        incoming = other.normalized()
        return LLMUsage(
            input_tokens=incoming.input_tokens or current.input_tokens,
            output_tokens=incoming.output_tokens or current.output_tokens,
            total_tokens=incoming.total_tokens or current.total_tokens,
            metadata={**current.metadata, **incoming.metadata},
        )


@dataclass
class LLMToolCall:
    """Normalized tool call emitted by a provider."""

    name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    id: str | None = None
    raw_arguments: str | None = None
    type: str = "tool_call"


@dataclass
class LLMResponse:
    """Normalized non-streaming response from a provider."""

    output_text: str = ""
    content: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[LLMToolCall] = field(default_factory=list)
    usage: LLMUsage | None = None
    stop_reason: str | None = None
    structured_output: Any = None
    model: str | None = None
    provider: str | None = None
    response_id: str | None = None
    raw: dict[str, Any] | list[Any] | None = None


@dataclass
class LLMChunk:
    """Streaming chunk from LLM."""

    type: str  # "content_block_delta", "message_stop", "error", ...
    delta: dict[str, Any] | str | None = None
    content: dict[str, Any] | None = None
    error: str | None = None
    usage: LLMUsage | None = None


class LLMClient:
    async def generate(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: dict[str, Any] | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """Generate one normalized response."""
        if type(self).complete is not LLMClient.complete:
            text = await self.complete(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
                tool_choice=tool_choice,
            )
            response = LLMResponse(
                output_text=text,
                structured_output=_parse_structured_output(text, response_format),
            )
            return self._store_response(response)
        raise NotImplementedError

    async def complete(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: dict[str, Any] | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        """Complete a chat request and return text only."""
        if type(self).generate is not LLMClient.generate:
            response = await self.generate(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
                tool_choice=tool_choice,
                response_format=response_format,
            )
            return response.output_text
        raise NotImplementedError

    async def complete_stream(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: dict[str, Any] | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> AsyncIterator[LLMChunk]:
        """Complete a chat request with streaming."""
        result = await self.complete(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            tool_choice=tool_choice,
            response_format=response_format,
        )
        yield LLMChunk(type="content_block_delta", delta=result)
        last_response = self.get_last_response()
        yield LLMChunk(type="message_stop", usage=last_response.usage if last_response else None)

    async def aclose(self) -> None:
        """Close provider resources."""
        return None

    def get_last_response(self) -> LLMResponse | None:
        return getattr(self, "_last_response", None)

    def _store_response(self, response: LLMResponse) -> LLMResponse:
        setattr(self, "_last_response", response)
        return response
