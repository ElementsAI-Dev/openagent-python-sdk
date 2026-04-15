# Examples

当前 repo 只保留两组维护中的 example：

1. `quickstart`
2. `production_coding_agent`

这样能保证 examples、docs 和 tests 三者保持一致，不再漂到已经删除的历史目录上。

## 环境变量

这两组 example 默认都使用 MiniMax 的 Anthropic-compatible 接口，需要：

- `MINIMAX_API_KEY`

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

### `production_coding_agent/`

高设计密度、production-style coding agent 示例：

- task packet assembly
- persistent coding memory
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

Benchmark：

```bash
uv run python examples/production_coding_agent/run_benchmark.py
```

## 配合文档一起看

建议配合：

- [docs/examples.md](../docs/examples.md)
- [docs/developer-guide.md](../docs/developer-guide.md)
- [docs/seams-and-extension-points.md](../docs/seams-and-extension-points.md)
- [docs/repository-layout.md](../docs/repository-layout.md)
