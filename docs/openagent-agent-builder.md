# OpenAgent Agent Builder

`openagent-agent-builder` 现在通过顶层 `skills` 组件发现和执行，不是 runtime 内的 seam。

它的目标是帮助主 agent 或开发者快速得到：

- 一个可运行的 single-agent `sdk_config`
- 一次 smoke run 结果
- 这个 agent 放进 team 里的接入建议

## 它负责什么

- build 一个 `subagent`
- build 一个 `agent-team` 里的单角色 agent
- 推导 `memory / pattern / tools / runtime`
- 输出 handoff contract 和 integration hints
- 用 `Runtime.from_dict(...)` 做一次 smoke run

## 它不负责什么

- 整个 team 的 scheduler
- mailbox / background jobs
- 全局 retry / cancel / resume
- 跨 agent 生命周期管理

## Core I/O

输入是 `OpenAgentSkillInput`：

- `task_goal`
- `agent_role`
- `agent_mode`
- `workspace_root`
- `available_tools`
- `constraints`
- `handoff_expectation`
- `overrides`
- `smoke_run`

输出是 `OpenAgentSkillOutput`：

- `agent_spec`
- `agent_prompt_summary`
- `design_rationale`
- `handoff_contract`
- `integration_hints`
- `smoke_result`
- `next_actions`

## Agent Spec Shape

`agent_spec` 尽量贴近 SDK 现有 schema，不额外发明 DSL。

它包含：

- `agent_key`
- `purpose`
- `sdk_config`
- `run_request_template`

因此可以直接用：

- `Runtime.from_dict(...)`
- `run_agent_with_dict(...)`

## Archetypes

v0 支持四个 archetype：

- `planner`
- `coder`
- `reviewer`
- `researcher`

它们只是默认模板，不是硬编码的 team 语义。

## Host Adapters

这套能力现在统一收在 skill 目录里：

- `skills/openagent-agent-builder/`
  - skill 文档、引用资料、examples
- `skills/openagent-agent-builder/src/openagent_agent_builder/`
  - 可执行 core
- `openagent_agent_builder.entrypoint.run_openagent_skill`
  - 给顶层 `skills` 组件或 app-owned main agent 调用

session 开始时，`skills.prepare_session()` 只预热 description；references 和 entrypoint 在需要时再渐进式加载。
