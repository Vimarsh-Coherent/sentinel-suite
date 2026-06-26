---
name: orchestrator
description: Multi-agent orchestration with Octogent. Use when the user wants to run many Claude Code sessions in parallel, "spawn agents", create a "tentacle" (scoped job folder), coordinate parallel work, or launch the Octogent dashboard. Ties spawned sessions to the undercover, code-graph, and ecc plugins.
---

# Orchestrator (powered by Octogent)

[Octogent](https://github.com/hesamsheikh/octogent) is a vendored Node.js
dashboard (`vendor/octogent/`) that orchestrates **many Claude Code sessions at
once**. Each job gets a **tentacle** — a folder under `.octogent/tentacles/<id>/`
with `CONTEXT.md` + `todo.md` — so agents work from durable scoped files instead
of messy chat history, and a coordinator can spawn child agents and message them.

> Octogent is an *application*, not a plugin or MCP server. It sits a layer
> **above** the other sentinel-suite plugins: the sessions it spawns can each load
> `undercover`, `code-graph`, and `ecc`.

## Launching it

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/launch_octogent.py"
# needs Node >= 22 and pnpm (the script runs `corepack enable pnpm` if missing).
# First run installs deps; UI opens at http://localhost:8787
```

## How it composes with the other plugins

When you create a tentacle for a slice of work, put guidance in its `CONTEXT.md`
so the spawned agent uses the right sentinel-suite capability:

| Tentacle kind | Point the agent at |
|---------------|--------------------|
| Code review / impact analysis | the **code-graph** skill (`build_or_update_graph_tool`, `get_impact_radius_tool`, `get_review_context_tool`) |
| Committing / opening PRs in a public repo | the **undercover** agent/skill (scrub internal info before commit) |
| TDD, security scan, language-specific work | the **ecc** skills/agents (271 skills, 67 agents) |

## Suggested workflow

1. Launch Octogent (above).
2. Create a tentacle per work-stream (docs, db, API, frontend).
3. In each tentacle's `CONTEXT.md`, name which sentinel-suite plugin(s) the agent
   should rely on and why.
4. Drive tasks from `todo.md`; spawn child agents per todo item.
5. Before any tentacle commits/opens a PR, have it run the **undercover** scan so
   nothing cover-blowing ships.

This is a learning setup — the goal is to feel how an orchestration layer,
code-intelligence, a harness library, and a guardrail plugin combine.
