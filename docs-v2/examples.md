# 示例说明

`examples/` 不是一堆随手写的 demo。  
每个示例都对应一种扩展姿势、一类 runtime seam、或一种 app-defined protocol 设计方式。

除特别说明外，大多数示例默认使用 MiniMax 的 Anthropic-compatible 接口，
需要 `MINIMAX_API_KEY`。

## 怎么选

- 第一次跑仓库
  - 先看 `quickstart`
- 学 `impl` 自定义插件
  - 先看 `custom_impl`
- 学 runtime seam 组合
  - 先看 `runtime_composition`
- 学完整 skill 生命周期
  - 先看 `skill_hooks_demo`
- 学高设计密度 coding agent
  - 先看 `production_coding_agent`
- 学自定义 multi-step pattern
  - 先看 `multi_step_research`
- 学长对话 / 长 session
  - 先看 `long_conversation`
- 学安全边界与文件权限
  - 先看 `sandbox_agent`
- 学持久化 memory
  - 先看 `persistent_qa`
- 学 OpenAI-compatible provider
  - 先看 `openai_compatible`

## `examples/quickstart/`

用途：

- 最小 builtin-only setup
- 第一次确认 kernel 能跑

关键文件：

- `agent.json`
- `run_demo.py`

展示内容：

- `window_buffer`
- `react`
- builtin search tool
- 同一个 session 下连续运行

运行：

```bash
uv run python examples/quickstart/run_demo.py
```

## `examples/custom_impl/`

用途：

- 演示如何直接用 `impl` 指向你自己的代码
- 自定义 pattern、skill、tool 一起工作

关键文件：

- `agent.json`
- `plugins.py`
- `run_demo.py`

展示内容：

- 自定义 skill
- 自定义 pattern
- 自定义 tool
- skill hook 对执行过程的影响

运行：

```bash
uv run python -m examples.custom_impl.run_demo
```

## `examples/runtime_composition/`

用途：

- 演示多个 runtime seam 如何围绕一个 agent 组合

关键文件：

- `agent.json`
- `plugins.py`
- `run_demo.py`
- `workspace/note.txt`

展示内容：

- `safe` tool executor
- `filesystem` execution policy
- `summarizing` context assembler
- custom pattern 消费 assembly metadata

运行：

```bash
uv run python examples/runtime_composition/run_demo.py
```

## `examples/skill_hooks_demo/`

用途：

- 单独观察 skill lifecycle

关键文件：

- `agent.json`
- `plugins.py`
- `run_demo.py`

展示内容：

- system prompt 注入
- metadata 注入
- context augment
- tool filter
- before-run
- after-run

运行：

```bash
uv run python examples/skill_hooks_demo/run_demo.py
```

## `examples/production_coding_agent/`

用途：

- 演示一个高设计密度、production-style 的 coding agent
- 展示“SDK seam + app-defined protocol”如何一起工作
- 展示严格的本地验证路径

关键文件：

- `agent.json`
- `plugins.py`
- `run_demo.py`
- `workspace/`
- `outputs/`
- `run_benchmark.py`
- `app/`
- `benchmarks/tasks.json`

展示内容：

- task packet assembly
- persistent coding memory
- engineering skill framing
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

验证：

```bash
uv run pytest -q tests/integration/test_production_coding_agent_example.py
```

Benchmark：

```bash
uv run python examples/production_coding_agent/run_benchmark.py
```

## `examples/multi_step_research/`

用途：

- 展示 custom multi-step pattern
- 演示 app-defined workflow 不必强行升级成新 seam

关键文件：

- `agent.json`
- `plugins.py`
- `run_demo.py`
- `workspace/notes.md`

展示内容：

- research-oriented custom pattern
- 多工具链路
- `state` / `scratch` 的使用

运行：

```bash
uv run python examples/multi_step_research/run_demo.py
```

## `examples/long_conversation/`

用途：

- 演示长 session 上下文控制

关键文件：

- `agent.json`
- `run_demo.py`

展示内容：

- `chain` memory
- `window_buffer`
- `summarizing` context assembler

运行：

```bash
uv run python examples/long_conversation/run_demo.py
```

## `examples/sandbox_agent/`

用途：

- 演示安全导向的 runtime 组合

关键文件：

- `agent.json`
- `plugins.py`
- `run_demo.py`
- `workspace/secret.txt`

展示内容：

- `filesystem` policy
- `safe` executor timeout
- custom pattern + 安全 seam

运行：

```bash
uv run python examples/sandbox_agent/run_demo.py
```

## `examples/persistent_qa/`

用途：

- 演示 file-backed custom memory

关键文件：

- `agent.json`
- `run_demo.py`
- `plugins/persistent_memory.py`

展示内容：

- 自定义持久化 memory
- `.agent_memory` 本地存储
- builtin pattern + app-owned memory 行为

运行：

```bash
uv run python examples/persistent_qa/run_demo.py
```

## `examples/openai_compatible/`

用途：

- 演示任意 OpenAI-compatible backend 的接法

关键文件：

- `.env.example`
- `agent.json`
- `run_demo.py`

需要的环境变量：

- `OPENAI_MODEL`
- `OPENAI_BASE_URL`
- `OPENAI_API_KEY`

运行：

```bash
uv run python examples/openai_compatible/run_demo.py
```

## 推荐阅读顺序

如果你想按最有效的顺序熟悉仓库，推荐：

1. `quickstart`
2. `custom_impl`
3. `runtime_composition`
4. `skill_hooks_demo`
5. `production_coding_agent`
6. `multi_step_research`
7. `long_conversation`
8. `sandbox_agent`
9. `persistent_qa`
10. `openai_compatible`

这个顺序可以让你先理解 kernel，再理解 seam，最后再看高设计密度 agent 示例。

## 继续阅读

- [开发者指南](developer-guide.md)
- [Seam 与扩展点](seams-and-extension-points.md)
- [配置参考](configuration.md)
- [插件开发](plugin-development.md)
- [API 参考](api-reference.md)
