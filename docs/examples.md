# 示例说明

当前仓库只保留两组维护中的 example。

这不是“缩水”，而是把仓库收回到真实、可跑、可测的维护面，避免文档继续引用已经删除的历史目录。

除特别说明外，这两组 example 都默认使用 MiniMax 的 Anthropic-compatible 接口，
需要 `MINIMAX_API_KEY`。

## 怎么选

- 第一次跑仓库
  - 先看 `quickstart`
- 想看一个高设计密度、贴近真实应用分层的例子
  - 看 `production_coding_agent`
- 想学自定义 plugin / seam
  - 先读 [插件开发](plugin-development.md)
  - 再看 `tests/fixtures/` 和 `examples/production_coding_agent/app/`

## `examples/quickstart/`

用途：

- 最小 builtin-only setup
- 第一次确认 kernel 能跑

关键文件：

- `examples/quickstart/agent.json`
- `examples/quickstart/run_demo.py`

展示内容：

- `window_buffer`
- `react`
- builtin search tool
- 同一个 session 下连续运行

运行：

```bash
uv run python examples/quickstart/run_demo.py
```

相关验证：

```bash
uv run pytest -q tests/integration/test_runtime_from_config_integration.py
```

## `examples/production_coding_agent/`

用途：

- 演示一个高设计密度、production-style 的 coding agent
- 展示“SDK seam + app-defined protocol”如何一起工作
- 展示严格的本地验证路径

关键文件：

- `examples/production_coding_agent/agent.json`
- `examples/production_coding_agent/run_demo.py`
- `examples/production_coding_agent/run_benchmark.py`
- `examples/production_coding_agent/app/`
- `examples/production_coding_agent/workspace/`
- `examples/production_coding_agent/outputs/`

展示内容：

- task packet assembly
- persistent coding memory
- filesystem boundary
- safe tool execution
- local follow-up semantics
- structured delivery artifacts
- benchmark-style local evaluation harness

它不是在宣称“本地测完就能直接投入市场”，而是在示范：

- 一个可成长的 coding agent 应该怎样分层
- 什么该放 seam
- 什么该放 app protocol
- 怎样把验证写成可复现的集成测试

运行：

```bash
uv run python examples/production_coding_agent/run_demo.py
```

Benchmark：

```bash
uv run python examples/production_coding_agent/run_benchmark.py
```

相关验证：

```bash
uv run pytest -q tests/integration/test_production_coding_agent_example.py
```

## 如果你想学自定义扩展

虽然当前 repo 不再保留一堆独立 demo 目录，但“怎么自定义”并没有消失，主要参考面是：

- `tests/fixtures/custom_plugins.py`
- `tests/fixtures/runtime_plugins.py`
- `tests/unit/test_plugin_loader.py`
- `tests/unit/test_runtime_orchestration.py`
- `examples/production_coding_agent/app/`

## 推荐阅读顺序

如果你想按最有效的顺序熟悉当前仓库，推荐：

1. `quickstart`
2. `production_coding_agent`
3. [插件开发](plugin-development.md)
4. [仓库结构](repository-layout.md)

## 继续阅读

- [开发者指南](developer-guide.md)
- [Seam 与扩展点](seams-and-extension-points.md)
- [配置参考](configuration.md)
- [插件开发](plugin-development.md)
- [API 参考](api-reference.md)
