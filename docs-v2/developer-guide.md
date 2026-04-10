# 开发者指南

这份文档不是“怎么跑一个 demo”，而是面向真正要基于 `openagent-py-sdk` 开发 agent、runtime 或上层产品的人。

它重点回答：

- 这套 SDK 的定位到底是什么
- 它为什么值得用
- 它的边界在哪里
- 如何用它做高设计密度 agent
- 遇到复杂问题时，应该改哪一层

## 一句话定位

`openagent-py-sdk` 是一个：

- 单 agent
- 配置驱动
- 插件化
- 异步优先
- runtime-first

的执行内核。

它不是现成的多 agent 产品，也不是完整的 Claude Code 替代品。  
它更像“可进化的单 agent kernel”，适合被更高层的 CLI、framework、control plane、research app 包起来。

## 为什么值得用

如果你要做的只是一个能回话的小 demo agent，这套 SDK 甚至可能显得有点重。

但如果你要做的是：

- coding agent
- research agent
- 长会话 agent
- 带权限控制和工具策略的 agent
- 上层 framework / control plane

那么它的优点就很明显了。

### 1. 内核协议是显式的

核心运行对象不是 ad-hoc dict，而是有清晰边界的结构化协议：

- `RunRequest`
- `RunResult`
- `ToolExecutionRequest`
- `ToolExecutionResult`
- `ContextAssemblyResult`

这让 runtime、pattern、tool、session 之间的边界稳定，不会因为业务需求增长就开始互相污染。

### 2. 中间层不是被 prompt 吞掉的

这套 SDK 的核心价值不是“支持 tool / memory / pattern”，而是承认 agent 的复杂度很多时候在 **middle protocols**：

- tool 怎么执行
- tool 能不能执行
- transcript 怎么进上下文
- follow-up 怎么解释
- provider 坏响应怎么修

如果没有这些 seam，所有复杂度最终都会回流到 pattern。

### 3. 适合开发者自己设计产品语义

SDK 不试图把所有产品层问题都预设好，而是提供 kernel + seam，让开发者自己设计：

- coding 风格的 follow-up
- action summary
- team / subagent orchestration
- provider-specific repair policy
- 长会话上下文装配策略

这对做高设计密度 agent 是好事，因为真正复杂的语义通常不该硬编码进 SDK core。

## 三层心智模型

理解这套 SDK 最容易的方式，是先把它分成三层：

### 1. SDK Core

固定协议，不轻易变化。

包括：

- `Runtime`
- `SessionManager`
- `EventBus`
- `RunRequest / RunResult`
- `ExecutionContext`
- `ToolExecutionRequest / Result`

### 2. SDK Seams

在固定协议上开放出来的策略扩展点。

包括：

- `memory`
- `pattern`
- `skill`
- `tool_executor`
- `execution_policy`
- `context_assembler`
- `followup_resolver`
- `response_repair_policy`

### 3. App / Product Layer

开发者自己定义的业务和产品语义。

包括：

- coding agent 行为
- follow-up 语义风格
- permission UX
- subagent / team
- mailbox / background task
- app-specific context engineering

关键原则是：

**固定 core 协议，开放 seam，保留产品语义自由。**

## 配置层级

### App 级

在顶层：

- `runtime`
- `session`
- `events`

它们决定整个应用如何运行。

### Agent 级

在 `agents[*]` 里：

- `memory`
- `pattern`
- `llm`
- `skill`
- `tools`
- `tool_executor`
- `execution_policy`
- `context_assembler`
- `followup_resolver`
- `response_repair_policy`
- `runtime`

要特别注意：

- 顶层 `runtime` 是 `RuntimeRef`
- agent 内 `runtime` 是 `RuntimeOptions`

前者是“选哪个 runtime plugin”，后者是“这次 agent 运行的预算参数”。

## 一次 Runtime.run 的执行链

最重要的主链是：

1. `Runtime.run()` 把简单输入包装成 `RunRequest`
2. `Runtime.run_detailed()` 找到目标 `AgentDefinition`
3. 通过 `load_agent_plugins()` 为 `(session_id, agent_id)` 解析或复用插件实例
4. 进入 `DefaultRuntime.run()`
5. 获取 session lock
6. `context_assembler.assemble()` 组装 transcript / artifacts
7. 绑定 tools、executor、policy
8. `pattern.setup(...)`
9. `memory.inject(...)`
10. skill hooks
11. `pattern.execute()`
12. `memory.writeback(...)`
13. append transcript
14. persist artifacts
15. 返回 `RunResult`

这条链说明了一个很重要的事实：

**pattern 不是整个世界，runtime 才是总协调者。**

## 什么时候改哪一层

### 改 Pattern

当你要改变的是：

- agent loop
- reasoning / acting 结构
- tool-use 回合编排
- LLM 交互格式

### 改 Memory

当你要改变的是：

- 历史如何注入
- 历史写回什么
- memory view 如何裁剪和投影

### 改 Tool Executor

当你要改变的是：

- tool timeout / retry / streaming
- tool result 规范化
- tool 执行包装

### 改 Execution Policy

当你要改变的是：

- allow / deny
- path whitelist
- 需要审批还是可直接执行

### 改 Context Assembler

当你要改变的是：

- transcript 裁剪
- artifact 选择
- session 上下文装配

### 改 Followup Resolver

当你要改变的是：

- “你刚干了什么”
- “刚才读到了什么”
- “上一轮为什么这么做”

这类多轮追问语义。

### 改 Response Repair Policy

当你要改变的是：

- empty response
- provider 空 turn
- 伪 tool-call
- tool-result 后模型不继续回答
- 坏格式修复

## 高阶 Python API

如果你不想所有接入都从 JSON 文件出发，现在有几条更友好的入口。

### 1. 从 dict 直接构造 Runtime

```python
from openagents import Runtime

runtime = Runtime.from_dict(payload)
```

适合：

- 测试
- notebook / research
- 上层框架动态生成 config

### 2. 直接从 dict 同步运行

```python
from openagents.runtime.sync import run_agent_with_dict

result = run_agent_with_dict(
    payload,
    agent_id="assistant",
    session_id="demo",
    input_text="hello",
)
```

### 3. 拿结构化结果而不是只拿 output

```python
from openagents.runtime.sync import run_agent_detailed

result = run_agent_detailed(
    "agent.json",
    agent_id="assistant",
    session_id="demo",
    input_text="hello",
)

print(result.final_output)
print(result.stop_reason)
print(result.usage)
```

### 4. 直接从已加载 config 运行

```python
from openagents import load_config_dict
from openagents.runtime.sync import run_agent_detailed_with_config

config = load_config_dict(payload)
result = run_agent_detailed_with_config(
    config,
    agent_id="assistant",
    session_id="demo",
    input_text="hello",
)
```

## 现在已经是一等公民的扩展点

支持 decorator / registry / `type` 的有：

- `tool`
- `memory`
- `pattern`
- `runtime`
- `skill`
- `session`
- `event_bus`
- `tool_executor`
- `execution_policy`
- `context_assembler`
- `followup_resolver`
- `response_repair_policy`

也就是说，核心 agent middle seams 现在都已经是一等公民扩展点了。

推荐选择方式：

- 本仓库内、本应用内开发：优先 decorator + `type`
- 跨包 / 发布后复用：优先 `impl`

## 适合什么，不适合什么

### 适合

- 你是 agent runtime / infra / platform 开发者
- 你希望保留中间层控制权
- 你要做 coding agent、research agent、framework kernel
- 你想把复杂度拆开，而不是糊在一个 Agent 类里

### 不适合

- 你想零配置快速做一个复杂产品级 agent
- 你要现成 multi-agent orchestration
- 你不打算读 runtime / loader / interfaces 源码

## 最重要的建议

以后如果你继续扩这套 SDK，最重要的是不要让所有复杂逻辑重新回流到 `Pattern.execute()`。

一旦：

- follow-up
- provider repair
- context packing
- tool execution quirks

又都堆回 pattern，这套 SDK 最有价值的地方就会被抵消。

最健康的演进方式是：

- core 协议稳定
- seam 逐步补齐
- 产品语义保持在 app 层
