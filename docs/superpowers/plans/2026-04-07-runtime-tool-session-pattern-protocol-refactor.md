# Runtime Tool Session Pattern Protocol Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce structured runtime contracts and middle-layer execution protocols so the SDK is runtime-semantics extensible, not only plugin-type extensible.

**Architecture:** Add typed contracts and protocols for run requests/results, tool execution, policy, transcript storage, and artifact storage. Keep the public `Runtime.run()` wrapper stable while rewiring the default runtime and execution context to use the new protocol path internally.

**Tech Stack:** Python 3.10+, dataclasses, existing plugin/capability system, pytest

---

### Task 1: Add protocol models to interface layer

**Files:**
- Modify: `openagents/interfaces/runtime.py`
- Modify: `openagents/interfaces/tool.py`
- Modify: `openagents/interfaces/session.py`
- Modify: `openagents/interfaces/pattern.py`

- [ ] Define typed request/result dataclasses and new protocol hooks.
- [ ] Keep old helper methods available where practical to reduce breakage.

### Task 2: Rewire default runtime to use the new contracts

**Files:**
- Modify: `openagents/plugins/builtin/runtime/default_runtime.py`
- Modify: `openagents/runtime/runtime.py`

- [ ] Build `RunRequest` in `Runtime.run()`.
- [ ] Translate old top-level return behavior from `RunResult`.
- [ ] Add default tool executor and allow-all execution policy.

### Task 3: Extend in-memory session manager

**Files:**
- Modify: `openagents/plugins/builtin/session/in_memory.py`

- [ ] Add transcript, artifact, and checkpoint support with simple in-memory data structures.
- [ ] Preserve existing state access and locking behavior.

### Task 4: Add targeted regression tests

**Files:**
- Modify: `tests/unit/test_runtime_core.py`
- Modify: `tests/unit/test_runtime_orchestration.py`
- Modify: `tests/unit/test_builtin_plugins_runtime.py`
- Add or modify as needed: `tests/unit/test_runtime_output_constraints.py`

- [ ] Add coverage for typed run results, session transcript/artifact behavior, and executor-backed tool calls.
- [ ] Keep the test surface focused on the new protocol seams.

### Task 5: Run verification

**Files:**
- No code changes expected

- [ ] Run `uv run pytest -q`
- [ ] Fix regressions until green
