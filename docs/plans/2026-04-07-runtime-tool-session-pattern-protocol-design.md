# Runtime / Tool / Session / Pattern Protocol Refactor Design

## Goal

Refactor the SDK's inner runtime contracts so complex coding-agent runtimes can be built above it without pushing orchestration, policy, and context-assembly semantics into individual patterns or tools.

## Problem

The current SDK already has plugin categories for runtime, session, pattern, tool, memory, skill, and events. The main extensibility gap is not missing plugin kinds, but missing middle-layer contracts:

- `RuntimePlugin.run()` accepts only loose scalar inputs and returns `Any`.
- `PatternPlugin` directly executes tools and implicitly owns too much context-management behavior.
- `ToolPlugin` lacks execution metadata for concurrency, interruption, policy, and result handling.
- `SessionManagerPlugin` stores an undifferentiated mutable state dict, which is insufficient for transcripts, artifacts, and checkpoints.

This makes higher-level coding-agent runtimes possible, but expensive to build cleanly.

## Design

### 1. Structured run contracts

Introduce typed runtime request/response models:

- `RunRequest`: carries agent/session identifiers plus metadata, budget, parent lineage, artifacts, and context hints.
- `RunResult`: carries final output, stop reason, usage, error, and artifacts.

`RuntimePlugin.run()` will accept a `RunRequest` and return a `RunResult`. The top-level `Runtime.run()` compatibility wrapper will keep the existing scalar call surface for now.

### 2. Tool execution seam

Introduce a `ToolExecutor` protocol and `ToolExecutionRequest` / `ToolExecutionResult` models.

Patterns should request tool execution through the executor rather than calling `tool.invoke()` directly. The default executor will remain simple, but the seam will allow later support for concurrency, streaming, approval policies, and cancellation without rewriting patterns.

### 3. Policy seam

Introduce an `ExecutionPolicy` protocol plus `PolicyDecision`.

The default runtime will ask policy before tool execution. The default policy will allow everything, preserving current behavior. This creates a stable point for future sandbox/permission systems.

### 4. Transcript and artifact storage semantics

Extend session contracts with typed transcript and artifact operations:

- append/load messages
- save/list artifacts
- create/load checkpoints

The in-memory session manager will provide a basic implementation so tests and examples continue to work.

### 5. Pattern boundary cleanup

Extend `ExecutionContext` to carry:

- `run_request`
- `tool_executor`
- `execution_policy`
- `usage`
- `artifacts`

Patterns remain responsible for strategy. Runtime regains ownership of run lifecycle and tool-execution coordination.

## Compatibility

- Keep top-level `Runtime.run(agent_id, session_id, input_text)` unchanged.
- Keep existing tool classes functional by adapting old `invoke()` / `invoke_stream()` methods into the new executor path.
- Keep existing patterns functional by providing default helper methods backed by the new executor.

## Non-Goals

- No teammate/subagent/team product layer in this refactor.
- No UI, terminal, or bridge features.
- No advanced scheduler yet; only the protocol seam and default implementation.

## Success Criteria

- Existing tests continue to pass with focused updates where needed.
- Runtime, pattern, tool, and session layers exchange typed contracts instead of ad hoc dict/`Any` values in the critical path.
- Future coding-agent runtimes can plug in policy, transcript storage, and tool execution control without changing pattern logic.
