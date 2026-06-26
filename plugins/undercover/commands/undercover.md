---
description: Show undercover status, or scan/redact commit & PR text for cover-blowing content.
argument-hint: "[status|scan|redact] [text...]"
allowed-tools: Bash(python:*)
---

Run the undercover utility for the user.

Arguments: `$ARGUMENTS`

- If the first word is `status` (or empty): run
  `python "${CLAUDE_PLUGIN_ROOT}/scripts/undercover.py" status` and explain the result.
- If it is `scan`: run
  `python "${CLAUDE_PLUGIN_ROOT}/scripts/undercover.py" scan --text "<rest of arguments>"`
  and summarise findings.
- If it is `redact`: run
  `python "${CLAUDE_PLUGIN_ROOT}/scripts/undercover.py" redact --text "<rest of arguments>"`
  and show the cleaned text.

If the user supplied raw text without a subcommand, default to `scan`.
