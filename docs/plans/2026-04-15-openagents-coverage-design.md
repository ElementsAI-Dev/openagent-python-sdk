# OpenAgents Coverage Design

## Goal

Raise automated test coverage for `openagents/` to at least 90 percent.

Coverage scope is intentionally narrow:

- include: `openagents/`
- exclude from the success metric: `docs/`, `tests/`, `examples/`, generated artifacts

This keeps the target aligned with the SDK kernel itself rather than the whole repo shell.

## Why Scope A

The current repository contains:

- SDK kernel code in `openagents/`
- documentation and repo-shape files
- maintained examples under `examples/`

The user chose coverage scope `A`, so the success metric should measure the SDK package, not example application code. Example tests can still help drive real behavior, but they do not count toward the required threshold unless they execute `openagents/` code.

## Approach

Use three layers:

1. coverage tooling in project dev dependencies and config
2. a baseline coverage run to identify the largest uncovered surfaces
3. focused TDD on the highest-value uncovered modules until total package coverage reaches 90 percent

## Expected Hotspots

Based on the current repo shape and existing tests, the likely gaps are:

- `openagents/__init__.py`
- `openagents/config/__init__.py`
- `openagents/plugins/__init__.py`
- `openagents/runtime/sync.py`
- `openagents/utils/build.py`
- `openagents/utils/hotreload.py`
- small interface/export modules
- provider helpers and registry branches not exercised by current tests

Large builtin runtime/pattern modules already have non-trivial coverage and should only be touched if the baseline says they are still major holes.

## Success Criteria

- project can run a repeatable coverage command with `uv`
- coverage report is scoped to `openagents/`
- total coverage is at least 90 percent
- new tests are behavior-oriented and follow red-green verification
- the final answer cites fresh command output
