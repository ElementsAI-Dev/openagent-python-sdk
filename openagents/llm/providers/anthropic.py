"""Anthropic-compatible LLM provider via reusable httpx transport."""

from __future__ import annotations

import json
import os
from typing import Any, AsyncIterator

from openagents.llm.base import LLMChunk, LLMResponse, LLMToolCall, LLMUsage
from openagents.llm.providers._http_base import HTTPProviderClient


def _parse_usage(payload: dict[str, Any] | None) -> LLMUsage | None:
    if not isinstance(payload, dict):
        return None
    return LLMUsage(
        input_tokens=int(payload.get("input_tokens", 0) or 0),
        output_tokens=int(payload.get("output_tokens", 0) or 0),
        total_tokens=int(payload.get("total_tokens", 0) or 0),
    ).normalized()


def _parse_tool_input(raw: Any) -> tuple[dict[str, Any], str | None]:
    if isinstance(raw, dict):
        return raw, json.dumps(raw, ensure_ascii=False)
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}, raw
        return parsed if isinstance(parsed, dict) else {}, raw
    return {}, None


class AnthropicClient(HTTPProviderClient):
    """Anthropic-compatible LLM client."""

    def __init__(
        self,
        *,
        api_base: str,
        model: str,
        api_key_env: str = "ANTHROPIC_API_KEY",
        timeout_ms: int = 30000,
        default_temperature: float | None = None,
        max_tokens: int = 1024,
        stream_endpoint: str | None = None,
    ) -> None:
        super().__init__(timeout_ms=timeout_ms)
        self.api_base = api_base.rstrip("/")
        self.model = model
        self.api_key_env = api_key_env
        self.default_temperature = default_temperature
        self.default_max_tokens = max_tokens
        self._stream_endpoint = stream_endpoint

    def _messages_endpoint(self) -> str:
        if self.api_base.endswith("/v1"):
            return f"{self.api_base}/messages"
        return f"{self.api_base}/v1/messages"

    def _stream_endpoint_url(self) -> str:
        if self._stream_endpoint:
            return self._stream_endpoint
        return self._messages_endpoint()

    def _build_headers(self) -> dict[str, str]:
        api_key = os.getenv(self.api_key_env, "")
        return {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }

    def _build_structured_output_tool(
        self,
        response_format: dict[str, Any] | None,
    ) -> tuple[str | None, dict[str, Any] | None]:
        if not isinstance(response_format, dict):
            return None, None

        response_type = str(response_format.get("type", "")).strip().lower()
        if response_type == "json_schema":
            schema_payload = response_format.get("json_schema", {})
            if not isinstance(schema_payload, dict):
                schema_payload = {}
            tool_name = str(schema_payload.get("name", "structured_output")).strip() or "structured_output"
            schema = schema_payload.get("schema")
            if not isinstance(schema, dict):
                schema = {"type": "object", "properties": {}}
        elif response_type in {"json", "json_object"}:
            tool_name = "structured_output"
            schema = {"type": "object", "properties": {}}
        else:
            return None, None

        return tool_name, {
            "name": tool_name,
            "description": "Return the structured output payload as JSON.",
            "input_schema": schema,
        }

    def _build_payload(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stream: bool = False,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: dict[str, Any] | None = None,
        structured_tool_name: str | None = None,
        structured_tool: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, str]]:
        chosen_model = model or self.model
        chosen_temp = self.default_temperature if temperature is None else temperature
        chosen_max_tokens = max_tokens or self.default_max_tokens

        anthropic_messages: list[dict[str, Any]] = []
        system_prompt = ""

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system_prompt = str(content)
            elif role in ("user", "assistant"):
                anthropic_messages.append({"role": role, "content": content})

        payload_tools = list(tools or [])
        chosen_tool_choice = tool_choice
        if structured_tool is not None:
            payload_tools.append(structured_tool)
            chosen_tool_choice = {"type": "tool", "name": structured_tool_name}

        payload: dict[str, Any] = {
            "model": chosen_model,
            "messages": anthropic_messages,
            "max_tokens": chosen_max_tokens,
        }
        if system_prompt:
            payload["system"] = system_prompt
        if chosen_temp is not None:
            payload["temperature"] = chosen_temp
        if payload_tools:
            payload["tools"] = payload_tools
        if chosen_tool_choice is not None:
            payload["tool_choice"] = chosen_tool_choice
        if stream:
            payload["stream"] = True

        return payload, self._build_headers()

    def _parse_sse_event(self, raw: bytes) -> tuple[str | None, str | None]:
        text = raw.decode("utf-8", errors="replace").strip()
        if not text:
            return None, None
        if text.startswith("{") or text.startswith("["):
            return None, text

        event_type: str | None = None
        data_str: str | None = None
        for line in text.split("\n"):
            line = line.rstrip("\r")
            if line.startswith("event:"):
                event_type = line[6:].strip()
            elif line.startswith("data:"):
                data_str = line[5:].strip()
        return event_type, data_str

    def _extract_stream_error(self, data: dict[str, Any]) -> str | None:
        error = data.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str) and message.strip():
                return message
            return json.dumps(error, ensure_ascii=False)
        if isinstance(error, str) and error.strip():
            return error

        base_resp = data.get("base_resp")
        if isinstance(base_resp, dict):
            status_code = base_resp.get("status_code")
            if status_code not in (None, 0, 200):
                status_msg = base_resp.get("status_msg")
                if isinstance(status_msg, str) and status_msg.strip():
                    return status_msg
                return json.dumps(base_resp, ensure_ascii=False)

        return None

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
        structured_tool_name, structured_tool = self._build_structured_output_tool(response_format)
        payload, headers = self._build_payload(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
            tools=tools,
            tool_choice=tool_choice,
            structured_tool_name=structured_tool_name,
            structured_tool=structured_tool,
        )
        response = await self._request(
            "POST",
            self._messages_endpoint(),
            headers=headers,
            json_body=payload,
        )
        if response.status_code != 200:
            raise RuntimeError(f"HTTP {response.status_code}: {response.text[:500]}")

        data = response.json()
        content_blocks = data.get("content", [])
        output_parts: list[str] = []
        normalized_content: list[dict[str, Any]] = []
        tool_calls: list[LLMToolCall] = []
        structured_output: Any = None

        for block in content_blocks:
            if not isinstance(block, dict):
                continue
            normalized_content.append(block)
            block_type = block.get("type")
            if block_type == "text":
                text = block.get("text", "")
                if isinstance(text, str):
                    output_parts.append(text)
            elif block_type == "tool_use":
                tool_name = str(block.get("name", ""))
                tool_input, raw_arguments = _parse_tool_input(block.get("input"))
                if structured_tool_name and tool_name == structured_tool_name:
                    structured_output = tool_input
                    continue
                tool_calls.append(
                    LLMToolCall(
                        id=block.get("id"),
                        name=tool_name,
                        arguments=tool_input,
                        raw_arguments=raw_arguments,
                        type="tool_use",
                    )
                )

        result = LLMResponse(
            output_text="".join(output_parts),
            content=normalized_content,
            tool_calls=tool_calls,
            usage=_parse_usage(data.get("usage")),
            stop_reason=data.get("stop_reason"),
            structured_output=structured_output,
            model=data.get("model"),
            provider="anthropic",
            response_id=data.get("id"),
            raw=data,
        )
        return self._store_response(result)

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
        structured_tool_name, structured_tool = self._build_structured_output_tool(response_format)
        payload, headers = self._build_payload(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            tools=tools,
            tool_choice=tool_choice,
            structured_tool_name=structured_tool_name,
            structured_tool=structured_tool,
        )

        latest_usage: LLMUsage | None = None
        pending_stop_reason: str | None = None
        tool_state: dict[int, dict[str, Any]] = {}

        async with await self._stream(
            "POST",
            self._stream_endpoint_url(),
            headers=headers,
            json_body=payload,
            read_timeout_s=120.0,
        ) as response:
            if response.status_code != 200:
                body = await response.aread()
                error_text = body.decode("utf-8", errors="replace")
                yield LLMChunk(type="error", error=f"HTTP {response.status_code}: {error_text[:500]}")
                return

            buffer = b""
            async for chunk in response.aiter_bytes():
                buffer += chunk
                while b"\n\n" in buffer:
                    record, buffer = buffer.split(b"\n\n", 1)
                    event_type, data_str = self._parse_sse_event(record)
                    if data_str is None:
                        continue

                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    error_text = self._extract_stream_error(data)
                    if error_text:
                        yield LLMChunk(type="error", error=error_text)
                        return

                    if event_type is None and "choices" in data:
                        usage = data.get("usage")
                        parsed_usage = _parse_usage(
                            {
                                "input_tokens": (usage or {}).get("prompt_tokens", 0),
                                "output_tokens": (usage or {}).get("completion_tokens", 0),
                                "total_tokens": (usage or {}).get("total_tokens", 0),
                            }
                            if isinstance(usage, dict)
                            else None
                        )
                        if parsed_usage is not None:
                            latest_usage = parsed_usage

                        for choice in data.get("choices", []):
                            if not isinstance(choice, dict):
                                continue
                            delta = choice.get("delta", {})
                            if not isinstance(delta, dict):
                                delta = {}

                            content_text = delta.get("content", "")
                            if isinstance(content_text, str) and content_text:
                                yield LLMChunk(
                                    type="content_block_delta",
                                    delta={"type": "text_delta", "text": content_text},
                                    content={"type": "text", "text": content_text},
                                )

                            tool_calls = delta.get("tool_calls", [])
                            if isinstance(tool_calls, list):
                                for tool_delta in tool_calls:
                                    if not isinstance(tool_delta, dict):
                                        continue
                                    index = int(tool_delta.get("index", 0) or 0)
                                    current = tool_state.setdefault(index, {})
                                    current_id = tool_delta.get("id") or current.get("id")
                                    if current_id:
                                        current["id"] = current_id

                                    function = tool_delta.get("function", {})
                                    if not isinstance(function, dict):
                                        function = {}
                                    name = function.get("name")
                                    if isinstance(name, str) and name:
                                        current["name"] = name
                                        yield LLMChunk(
                                            type="content_block_start",
                                            content={
                                                "type": "tool_use",
                                                "id": current.get("id"),
                                                "name": name,
                                            },
                                        )
                                    arguments = function.get("arguments")
                                    if isinstance(arguments, str) and arguments:
                                        yield LLMChunk(
                                            type="content_block_delta",
                                            delta={"type": "input_json_delta", "partial_json": arguments},
                                        )

                            finish_reason = choice.get("finish_reason")
                            if isinstance(finish_reason, str) and finish_reason:
                                pending_stop_reason = (
                                    "tool_use" if finish_reason == "tool_calls" else finish_reason
                                )

                        if pending_stop_reason is not None and latest_usage is not None:
                            yield LLMChunk(
                                type="message_stop",
                                content={"stop_reason": pending_stop_reason},
                                usage=latest_usage,
                            )
                            pending_stop_reason = None
                        continue

                    if event_type == "message_start":
                        message = data.get("message", {})
                        if isinstance(message, dict):
                            usage = _parse_usage(message.get("usage"))
                            if usage is not None:
                                latest_usage = usage
                        yield LLMChunk(type="message_start", content=data, usage=latest_usage)
                    elif event_type == "content_block_start":
                        yield LLMChunk(
                            type="content_block_start",
                            content=data.get("content_block", data),
                            usage=latest_usage,
                        )
                    elif event_type == "content_block_delta":
                        yield LLMChunk(
                            type="content_block_delta",
                            delta=data.get("delta", {}),
                            content=data,
                            usage=latest_usage,
                        )
                    elif event_type == "content_block_stop":
                        yield LLMChunk(type="content_block_stop", content=data, usage=latest_usage)
                    elif event_type == "ping":
                        continue
                    elif event_type == "message_delta":
                        usage_payload = data.get("usage")
                        if isinstance(usage_payload, dict):
                            input_tokens = (
                                latest_usage.input_tokens
                                if latest_usage is not None
                                else int(usage_payload.get("input_tokens", 0) or 0)
                            )
                            output_tokens = int(
                                usage_payload.get(
                                    "output_tokens",
                                    latest_usage.output_tokens if latest_usage is not None else 0,
                                )
                                or 0
                            )
                            total_tokens = int(usage_payload.get("total_tokens", 0) or 0)
                            if total_tokens <= 0:
                                total_tokens = input_tokens + output_tokens
                            latest_usage = LLMUsage(
                                input_tokens=input_tokens,
                                output_tokens=output_tokens,
                                total_tokens=total_tokens,
                            )
                        delta = data.get("delta", {})
                        if isinstance(delta, dict):
                            stop_reason = delta.get("stop_reason")
                            if isinstance(stop_reason, str) and stop_reason:
                                pending_stop_reason = stop_reason
                        yield LLMChunk(type="message_delta", content=data, usage=latest_usage)
                    elif event_type == "message_stop":
                        yield LLMChunk(
                            type="message_stop",
                            content={"stop_reason": pending_stop_reason} if pending_stop_reason else {},
                            usage=latest_usage,
                        )
                        pending_stop_reason = None
                    elif event_type == "error":
                        yield LLMChunk(
                            type="error",
                            error=data.get("error", {}).get("message", str(data)),
                            usage=latest_usage,
                        )
                        return

            if buffer.strip():
                event_type, data_str = self._parse_sse_event(buffer)
                if data_str is not None:
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        data = None
                    if isinstance(data, dict):
                        error_text = self._extract_stream_error(data)
                        if error_text:
                            yield LLMChunk(type="error", error=error_text)
                            return

            if pending_stop_reason is not None:
                yield LLMChunk(
                    type="message_stop",
                    content={"stop_reason": pending_stop_reason},
                    usage=latest_usage,
                )

        self._store_response(
            LLMResponse(
                usage=latest_usage,
                stop_reason=pending_stop_reason,
                provider="anthropic",
            )
        )
