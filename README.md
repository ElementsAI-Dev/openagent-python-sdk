# OpenAgents SDK

Build protocol-rich agents on top of a small, explicit runtime kernel.

OpenAgents is a config-as-code, async-first, pluggable SDK for teams that want a
clear agent runtime, a few strong runtime seams, and enough room to invent their
own product-specific middle protocols.

语言 / Language:

- [English](README_EN.md)
- [简体中文](README_CN.md)

## What Makes It Different

- **Single-agent kernel, by design**
  - one `run` executes one `agent_id`; team orchestration belongs above the SDK
- **Protocol-first runtime**
  - explicit objects such as `RunRequest`, `RunResult`, `ExecutionContext`,
    `ToolExecutionRequest`, and `SessionArtifact`
- **A small set of high-value seams**
  - `tool_executor`, `execution_policy`, `context_assembler`,
    `followup_resolver`, `response_repair_policy`
- **Room for application-defined protocols**
  - task envelopes, review contracts, permission state, artifact taxonomies, and
    other product semantics live in app space instead of bloating the kernel

```text
App / Product Protocols
    task envelopes, coding plans, review contracts, approvals, UI semantics
            |
            v
SDK Runtime Seams
    tool_executor, execution_policy, context_assembler,
    followup_resolver, response_repair_policy
            |
            v
Kernel Protocols
    RunRequest, RunResult, ExecutionContext,
    ToolExecutionRequest, ToolExecutionResult, SessionArtifact
```

## Quick Start

Install:

```bash
uv add openagents-sdk
```

Minimal config:

```json
{
  "version": "1.0",
  "agents": [
    {
      "id": "assistant",
      "name": "demo-agent",
      "memory": {"type": "window_buffer", "on_error": "continue"},
      "pattern": {"type": "react"},
      "llm": {"provider": "mock"},
      "tools": [
        {"id": "search", "type": "builtin_search"}
      ]
    }
  ]
}
```

Usage:

```python
import asyncio

from openagents import Runtime


async def main() -> None:
    runtime = Runtime.from_config("agent.json")
    result = await runtime.run(
        agent_id="assistant",
        session_id="demo",
        input_text="hello",
    )
    print(result)


asyncio.run(main())
```

## Read More

- [English README](README_EN.md)
- [中文 README](README_CN.md)
- [Developer Docs](docs-v2/README.md)
- [Examples](docs-v2/examples.md)
