# Agent Rules

- Use `uv` for Python environment and dependency management.
- Install/sync dependencies with `uv sync`.
- Run project commands with `uv run ...`.
- Prefer `uv add ...` for adding new dependencies instead of `pip install`.
- When adding, removing, or changing code under `openagents/`, add, remove, or update the corresponding tests in the same change.
