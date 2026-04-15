# Repo Closure Design

## Background

The repository is already mid-migration:

- `docs-v2/` has been replaced in the working tree by `docs/`
- root `README.md` has been removed, while `pyproject.toml` still points to it
- multiple example directories were removed from `examples/`
- documentation and tests still reference deleted paths such as `docs-v2/`, `openagent_cli/`, `examples/custom_impl/`, and `examples/runtime_composition/`

The result is a repo that still has good kernel code, but an uneven outer shape:

- docs navigation is no longer accurate
- packaging metadata is incomplete
- tests describe historical surfaces instead of the current repo
- local cache and build artifacts add noise

## Goal

Turn the current working tree into a clean, accurate SDK repository with:

- one documentation tree: `docs/`
- one valid package landing page: `README.md`
- one accurate example index that matches the real `examples/` directory
- one test surface that validates current repo structure instead of deleted subsystems
- local cache and build artifacts removed from the workspace

## Non-Goals

This closure does not change the SDK kernel boundary itself:

- no new runtime seam design
- no new provider behavior
- no new example families
- no attempt to restore deleted `openagent_cli/` or removed historical examples

## Repository Decisions

### 1. Documentation Topology

Use a strict three-layer documentation layout:

- root `README.md`
  - short landing page for package users and package metadata
- `README_EN.md` and `README_CN.md`
  - full narrative project descriptions
- `docs/`
  - developer documentation, repo structure, configuration, extension guides, example guide

### 2. Example Policy

Document only examples that exist in the tree.

Current maintained examples:

- `examples/quickstart/`
- `examples/production_coding_agent/`

Historical example names should be removed from docs and tests unless they are restored as real directories.

### 3. Test Policy

Replace stale repo-shape assertions with current repo-shape assertions.

Add tests for:

- `pyproject.toml` readme path exists
- `.gitignore` does not ignore core tracked documentation/example paths
- docs no longer reference `docs-v2/`
- docs and readmes only reference example directories that actually exist

Remove tests tied to deleted subsystems:

- `openagent_cli`
- removed example directories

### 4. Cleanup Policy

Delete regenerable local artifacts inside the repo:

- `__pycache__/`
- `*.pyc`
- `.pytest_cache/`
- `.coverage`
- `dist/`
- `openagents_sdk.egg-info/`

Do not delete working environment/tool state that is still useful for local execution:

- `.venv/`
- `.uv-cache/`
- `.ace-tool/`
- `.claude/`

## File Map

### Create

- `README.md`
- `docs/repository-layout.md`
- `docs/plans/2026-04-15-repo-closure-design.md`
- `docs/plans/2026-04-15-repo-closure-implementation-plan.md`
- `tests/unit/test_repository_layout.py`

### Modify

- `.gitignore`
- `README_EN.md`
- `README_CN.md`
- `docs/README.md`
- `docs/examples.md`
- `docs/plugin-development.md`
- `examples/README.md`

### Delete

- stale `openagent_cli` test files
- stale deleted-example integration tests

## Validation

Minimum validation for closure:

- targeted red/green cycle on repo-structure tests
- full `uv run pytest -q`
- workspace caches removed without touching `.venv/`

## Expected Outcome

After closure, the repository should read as one coherent SDK:

- package entrypoint works
- docs point to real files
- examples guide matches the real tree
- tests describe the current repo instead of historical leftovers
- the workspace is visually cleaner and easier to navigate
