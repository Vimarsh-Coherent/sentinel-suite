---
name: undercover
description: Re-creation of Claude Code's internal "Undercover Mode". Scan or redact git commit messages / PR text so they never leak internal codenames, unreleased model versions, internal tooling/Slack/short-links, AI attribution, or the phrase "Claude Code". Use when the user mentions "undercover", "scrub commit", "redact PR", "cover-safe message", "don't leak internal names", or before committing in a public repo.
---

# Undercover Mode (learning skill)

A faithful, educational re-creation of the (ANT-only) Undercover Mode documented
in the `claurst` clean-room spec. All logic lives in
`${CLAUDE_PLUGIN_ROOT}/scripts/undercover.py` (pure stdlib Python).

## When to use

- The user asks to scrub / redact / sanitize a commit message or PR text.
- Before committing or opening a PR in a public/open-source repo.
- The user wants to understand how Undercover Mode works.

## How it activates (`is_undercover`)

1. `CLAUDE_CODE_UNDERCOVER=1` → forced ON (even in internal repos).
2. `CLAUDE_CODE_USER_TYPE` must be `ant` (defaults to `ant` here so it's
   demonstrable) — otherwise not applicable.
3. Automatic: ON unless the git `origin` remote is on the internal allowlist.
4. **No force-OFF**: if we're not confident the repo is internal, stay undercover.

Check it: `python "${CLAUDE_PLUGIN_ROOT}/scripts/undercover.py" status`

## What it catches

internal codenames (Tengu, Capybara…) · unreleased versions (opus-4-7…) ·
internal repo/project names · internal tooling, Slack channels, `go/` links ·
internal domains (`*.ant.dev`) · the phrase "Claude Code" · AI admissions ·
attribution / `Co-Authored-By` lines.

## Commands

```bash
# Inspect activation
python "${CLAUDE_PLUGIN_ROOT}/scripts/undercover.py" status

# Print the system-prompt block the hooks inject
python "${CLAUDE_PLUGIN_ROOT}/scripts/undercover.py" prompt

# Scan text (exit 1 if anything found) — human or --json
python "${CLAUDE_PLUGIN_ROOT}/scripts/undercover.py" scan --text "fix tengu cache, Co-Authored-By: Claude"
python "${CLAUDE_PLUGIN_ROOT}/scripts/undercover.py" scan -f message.txt --json

# Auto-redact and print clean text
python "${CLAUDE_PLUGIN_ROOT}/scripts/undercover.py" redact -f message.txt
```

## Customising the wordlist

Drop a `.undercover.json` in the repo root:

```json
{ "terms": ["projectatlas", "bluefin", "raven"] }
```

These terms are added to the built-in codename list for both scanning and
redaction.

## Optional: install as a real git hook

To enforce on plain `git commit` (outside Claude Code), copy the check into a
`commit-msg` hook:

```bash
# .git/hooks/commit-msg  (make executable)
python /path/to/sentinel-suite/scripts/undercover.py check-commit "$1"
```

## Note

This is a learning artifact that re-implements publicly documented *behaviour*
— it scrubs your own outgoing VCS text. It is not a tool for evading review or
hiding wrongdoing; use it to practice writing clean, attribution-free commits.
