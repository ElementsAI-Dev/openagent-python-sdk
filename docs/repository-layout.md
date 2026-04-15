# Repository Layout

这份文档只回答一个问题：当前仓库里每一层目录到底负责什么。

## Top Level

```text
openagent-py-sdk/
  README.md
  README_EN.md
  README_CN.md
  pyproject.toml
  uv.lock
  openagents/
  docs/
  examples/
  tests/
```

## Directory Responsibilities

### `openagents/`

SDK 主源码。

主要包含：

- config loader / schema
- runtime facade
- builtin runtime
- builtin plugin registry
- provider clients
- plugin interfaces

### `docs/`

唯一的开发者文档树。

推荐入口：

- [docs/README.md](README.md)
- [docs/developer-guide.md](developer-guide.md)
- [docs/seams-and-extension-points.md](seams-and-extension-points.md)
- [docs/examples.md](examples.md)

### `examples/`

当前仓库里维护中的可运行示例。

目前只保留两组：

- `quickstart/`
  - 最小 kernel 运行入口
- `production_coding_agent/`
  - 高设计密度、app-defined protocol 风格示例

`examples/README.md` 负责例子导航，`docs/examples.md` 负责更完整的学习顺序和定位说明。

### `tests/`

验证当前 repo truth，而不是历史遗留结构。

- `tests/unit/`
  - loader、runtime、provider、repo structure 等单元验证
- `tests/integration/`
  - config/example 级集成验证

## Documentation Topology

为避免重复和漂移，当前文档分工固定为：

- `README.md`
  - 包入口、最短上手路径、导航
- `README_EN.md` / `README_CN.md`
  - 完整项目说明
- `docs/`
  - 开发文档和结构文档
- `examples/README.md`
  - 示例目录导航

## What Is Intentionally Absent

当前 repo 不再把下面这些历史表面当成现役结构：

- `docs-v2/`
- `openagent_cli/`
- 已删除的旧 example 目录

如果未来要恢复它们，应该以真实目录和真实测试一起恢复，而不是只留文档引用。
