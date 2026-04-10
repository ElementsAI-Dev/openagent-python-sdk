from __future__ import annotations

import pytest

import openagents.llm.registry as llm_registry
from openagents.llm.base import LLMClient
from openagents.runtime.runtime import Runtime


class _CustomExampleLLMClient(LLMClient):
    async def complete(
        self,
        *,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[dict] | None = None,
        tool_choice: dict | None = None,
    ) -> str:
        _ = (messages, model, temperature, max_tokens, tools, tool_choice)
        return '{"type":"final","content":"custom: hello example"}'


@pytest.mark.asyncio
async def test_runtime_from_repo_custom_impl_example(monkeypatch):
    monkeypatch.setattr(llm_registry, "create_llm_client", lambda llm: _CustomExampleLLMClient())
    runtime = Runtime.from_config("examples/custom_impl/agent.json")

    result = await runtime.run(
        agent_id="custom-agent",
        session_id="custom-example",
        input_text="hello example",
    )

    assert result.startswith("custom:")
    await runtime.close()
