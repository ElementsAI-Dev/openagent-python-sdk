# Plugin Interface Seam Consolidation

**Date:** 2026-04-18  
**Status:** Draft

## Problem

The SDK currently has 11 top-level seams wired by the plugin loader. Three of them —
`execution_policy`, `followup_resolver`, `response_repair_policy` — are conceptually
subordinate to existing plugins rather than truly independent extension points. This
inflates the seam count, adds three config keys, complicates `pattern.setup()`, and
signals false equivalence between them and genuinely independent seams like `memory`
and `context_assembler`.

## Decision

Absorb the three subordinate seams into their natural owner plugins as ordinary
override methods with sensible defaults. Remove them as top-level loader slots and
config keys. Use the existing Python method-override idiom — no new hook registry,
no callback chain, no new terminology.

## Interface Changes

### `ToolExecutorPlugin` — add `evaluate_policy`

```python
class ToolExecutorPlugin(BasePlugin):
    async def evaluate_policy(
        self, request: ToolExecutionRequest
    ) -> PolicyDecision:
        """Override to restrict tool execution. Default: allow all."""
        return PolicyDecision(allowed=True)

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        decision = await self.evaluate_policy(request)
        if not decision.allowed:
            return ToolExecutionResult(
                tool_id=request.tool_id,
                success=False,
                error=f"policy denied: {decision.reason}",
            )
        # ... existing execution logic
```

Policy is always global (applies to all tools going through the executor). Per-tool
metadata that informs policy decisions continues to live in `ToolPlugin.execution_spec()`.

### `PatternPlugin` — add `resolve_followup` and `repair_response`

```python
class PatternPlugin(BasePlugin):
    async def resolve_followup(
        self, query: str, context: RunContext[Any]
    ) -> FollowupResult:
        """Override to answer follow-ups locally. Default: abstain (call LLM)."""
        return FollowupResult(status="abstain")

    async def repair_response(
        self, response: str, context: RunContext[Any]
    ) -> RepairResult:
        """Override to handle bad LLM responses. Default: abstain (propagate)."""
        return RepairResult(status="abstain")
```

Pattern is the natural owner because it has full visibility into what happened during
the run (transcript, tool results, usage).

### `PatternPlugin.setup()` — remove three parameters

Remove `followup_resolver`, `response_repair_policy`, and `execution_policy` from the
`setup()` signature. `tool_executor` stays because the executor is still independently
substitutable.

## Seam Inventory After Change

| Seam | Status | Reason |
|---|---|---|
| `pattern` | keep | core loop |
| `memory` | keep | independent lifecycle (inject / writeback) |
| `context_assembler` | keep | runs before pattern, independent lifecycle |
| `tool_executor` | keep | independently substitutable engine |
| `events` | keep | cross-cutting infrastructure |
| `runtime` / `session` / `skills` | keep | app infrastructure |
| `execution_policy` | **removed** | absorbed into `ToolExecutorPlugin.evaluate_policy()` |
| `followup_resolver` | **removed** | absorbed into `PatternPlugin.resolve_followup()` |
| `response_repair_policy` | **removed** | absorbed into `PatternPlugin.repair_response()` |

Seam count: 11 → 8.

## Config Impact

Remove three keys from agent config schema:

```diff
- execution_policy: ...
- followup_resolver: ...
- response_repair_policy: ...
```

Developers who need custom policy or repair behavior subclass the relevant plugin and
override the method. No separate config entry required.

## Loader Impact

`plugins/loader.py` and `plugins/registry.py` no longer need to resolve or wire the
three removed slots. `DefaultRuntime.run()` no longer passes them to `pattern.setup()`.

## Migration

Existing standalone `execution_policy` / `followup_resolver` / `response_repair_policy`
plugins can be adapted by wrapping them in a `ToolExecutorPlugin` or `PatternPlugin`
subclass. Each adapter is under 10 lines.

## What This Is Not

- Not a hook system. No registration, no pre/post chain, no new terminology.
- Not removing any capability. Every behavior expressible before is still expressible.
- Not touching `memory`, `context_assembler`, or any app infrastructure seam.
