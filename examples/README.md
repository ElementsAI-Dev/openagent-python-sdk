# Examples

这些 example 按扩展姿势组织，不按“简单到复杂”组织。

如果你是第一次看仓库，推荐顺序：

1. `quickstart`
2. `custom_impl`
3. `runtime_composition`
4. `production_coding_agent`

这样最容易先看懂 kernel，再看懂 seam，最后看高设计密度 agent。

## 模型说明

大多数 example 默认使用 MiniMax 的 Anthropic-compatible 接口，需要：

- `MINIMAX_API_KEY`

`openai_compatible/` 例外，它需要：

- `OPENAI_MODEL`
- `OPENAI_BASE_URL`
- `OPENAI_API_KEY`

## 目录说明

### `quickstart/`

builtin-only 最小示例：

- builtin memory
- builtin pattern
- builtin search tool

运行：

```bash
uv run python examples/quickstart/run_demo.py
```

### `custom_impl/`

直接用 `impl` 指向自定义代码：

- custom pattern
- custom skill
- custom tool

运行：

```bash
uv run python -m examples.custom_impl.run_demo
```

### `runtime_composition/`

演示 agent 级 runtime seam：

- `tool_executor`
- `execution_policy`
- `context_assembler`

运行：

```bash
uv run python examples/runtime_composition/run_demo.py
```

### `skill_hooks_demo/`

演示完整 skill lifecycle：

- system prompt
- metadata
- context augment
- tool filter
- before run
- after run

运行：

```bash
uv run python examples/skill_hooks_demo/run_demo.py
```

### `production_coding_agent/`

高设计密度、production-style coding agent 示例：

- task packet assembly
- persistent coding memory
- engineering skill framing
- filesystem boundary
- safe tool execution
- local follow-up semantics
- delivery artifacts

运行：

```bash
uv run python examples/production_coding_agent/run_demo.py
```

验证：

```bash
uv run pytest -q tests/integration/test_production_coding_agent_example.py
```

### `multi_step_research/`

自定义 research pattern 示例。

运行：

```bash
uv run python examples/multi_step_research/run_demo.py
```

### `long_conversation/`

长对话 / 长 session 示例：

- `chain` memory
- `window_buffer`
- `summarizing` context assembler

运行：

```bash
uv run python examples/long_conversation/run_demo.py
```

### `sandbox_agent/`

安全导向示例：

- `filesystem` execution policy
- `safe` tool executor

运行：

```bash
uv run python examples/sandbox_agent/run_demo.py
```

### `persistent_qa/`

自定义持久化 memory 示例。

运行：

```bash
uv run python examples/persistent_qa/run_demo.py
```

### `openai_compatible/`

OpenAI-compatible provider 示例。

运行：

```bash
uv run python examples/openai_compatible/run_demo.py
```

## 配合文档一起看

建议配合：

- [docs-v2/examples.md](../docs-v2/examples.md)
- [docs-v2/developer-guide.md](../docs-v2/developer-guide.md)
- [docs-v2/seams-and-extension-points.md](../docs-v2/seams-and-extension-points.md)
