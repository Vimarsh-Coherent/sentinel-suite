---
description: Launch the Octogent multi-agent dashboard, or scaffold a tentacle.
argument-hint: "[launch|tentacle <name>]"
allowed-tools: Bash(python:*), Write
---

Handle the user's orchestration request: `$ARGUMENTS`

- `launch` (or empty): run
  `python "${CLAUDE_PLUGIN_ROOT}/scripts/launch_octogent.py"` and tell the user
  the dashboard opens at http://localhost:8787. Note it needs Node >= 22 and pnpm.
- `tentacle <name>`: create `.octogent/tentacles/<name>/CONTEXT.md` and
  `.octogent/tentacles/<name>/todo.md` for the named slice of work. In
  `CONTEXT.md`, state the scope and which sentinel-suite plugin(s) the agent should
  use (code-graph for impact analysis, undercover before commits, ecc for
  language/TDD/security skills). Seed `todo.md` with a first checklist item.

If the user is unsure, explain that Octogent orchestrates multiple Claude Code
sessions and each can load the undercover / code-graph / ecc plugins.
