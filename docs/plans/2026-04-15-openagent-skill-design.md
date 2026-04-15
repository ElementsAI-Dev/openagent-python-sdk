# OpenAgent Skill Design

## Goal

Build `openagent` into a developer-facing high-level skill that helps a main agent or a human developer quickly:

- synthesize one runnable single-agent spec on top of `openagent-sdk`
- explain why that agent design was chosen
- provide integration hints for a larger team
- run one single-agent smoke test to prove the spec is at least runnable

The skill must support two hosts:

- Codex / Claude Code style skill systems
- an app-owned main agent calling the same capability as a high-level tool/skill

## Ground Truth Boundary

`openagent-sdk` remains a **single-agent kernel**.

That means:

- one `Runtime.run()` executes one `agent_id`
- SDK `SkillPlugin` remains a single-run augmentation seam
- multi-agent orchestration stays above the SDK

This project does **not** convert the SDK itself into a multi-agent runtime.

## Core Architecture

The system has one core truth and two thin host adapters.

```text
openagent-sdk
  = single-agent kernel

openagent-skill-core
  = input normalization
  + archetype selection
  + sdk config rendering
  + smoke run

host adapter A
  = Codex / Claude Code skill

host adapter B
  = main-agent callable tool/skill
```

### Why One Core Truth

Both hosts should call the same core behavior so that:

- the skill only has one mental model
- docs only describe one workflow
- tests validate one builder/smoke path
- future refinements do not drift across two separate implementations

## What The Skill Is

`openagent skill` is an **agent builder + smoke runner**.

It is for building:

- one `subagent`
- or one role agent inside a larger `agent-team`

It is **not** a full team runner.

## What The Skill Does

The v0 skill is responsible for:

- accepting a task/role-oriented request from a host
- selecting an agent archetype
- deriving a runnable single-agent SDK config
- producing integration guidance for use inside a team
- running one smoke test against the generated spec

The v0 skill is not responsible for:

- global team scheduling
- mailbox / background jobs
- cross-agent lifecycle management
- full team retry / cancel / resume
- top-level orchestration policy

## Input / Output Protocol

### Input: `OpenAgentSkillInput`

The core input object is:

- `task_goal`
- `agent_role`
- `agent_mode`
  - `subagent`
  - `team-role`
- `workspace_root`
- `available_tools`
- `constraints`
- `handoff_expectation`
- `overrides`
- `smoke_run`

### Output: `OpenAgentSkillOutput`

The core output object is:

- `agent_spec`
- `agent_prompt_summary`
- `design_rationale`
- `handoff_contract`
- `integration_hints`
- `smoke_result`
- `next_actions`

The most important field is `agent_spec`.

## Agent Spec Shape

The generated spec should stay as close as possible to the SDK’s current schema.

Instead of inventing a new DSL, the skill should output an **AppConfig-compatible single-agent bundle**:

- `agent_key`
- `purpose`
- `sdk_config`
  - full `AppConfig`-compatible object
  - exactly one agent inside `agents`
- `run_request_template`

This keeps the generated result directly runnable with:

- `Runtime.from_dict(...)`
- `run_agent_with_dict(...)`

## Internal Decision Pipeline

The core builder should always follow the same six-step process:

1. Normalize input
2. Select archetype
3. Derive SDK components
4. Apply overrides
5. Render runnable spec
6. Run smoke test

This is intentionally constrained synthesis rather than free-form config generation.

## Archetypes

v0 supports four built-in archetypes:

- `planner`
- `coder`
- `reviewer`
- `researcher`

Each archetype provides defaults for:

- memory
- pattern
- tool mix
- runtime budget posture
- optional skill framing
- integration expectations

The archetype is a starting point, not a hard lock.

## Smoke Run Contract

The smoke run exists to prove:

- config loads
- plugins instantiate
- runtime can execute one agent run
- the resulting shape is not obviously broken

The smoke run does **not** prove:

- the agent is correct for a real team
- the larger team orchestration is valid
- the business task is solved

## Host Adapters

### Host Adapter A: Codex / Claude Code Skill

Deliver as a repo-contained skill folder with:

- `SKILL.md`
- `agents/openai.yaml`
- optional `references/`

The skill should teach the host how to:

- ask for the right inputs
- generate one agent spec
- run the smoke path
- hand the result back to the user

### Host Adapter B: Main Agent Tool / Skill

Deliver as a callable Python entrypoint around the same core builder.

The main agent adapter should:

- accept structured input
- call the shared builder
- return structured output

It should not own a separate orchestration policy.

## Suggested Repo Layout

```text
skills/
  openagent-agent-builder/
    SKILL.md
    agents/
      openai.yaml
    references/
      architecture.md
      archetypes.md
      examples.md

openagents/
  agent_builder/
    __init__.py
    models.py
    archetypes.py
    normalize.py
    render.py
    smoke.py
    builder.py
    host_adapter.py
```

This layout keeps:

- host skill artifacts separate from SDK runtime code
- reusable builder logic importable from Python
- documentation and testing anchored on the same shared core

## Success Criteria

The implementation is successful when:

- developers can invoke one skill/tool and get back a runnable single-agent spec
- the same core builder is used by both supported hosts
- the generated spec runs through one smoke test
- the skill remains clearly above the single-agent kernel boundary
- the resulting system helps a main agent build one subagent or one team-role agent quickly and repeatably
