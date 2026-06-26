# Sentinel Suite

A small, learning-oriented **Claude Code plugin** built while studying three
projects:

- [`code-review-graph`](https://github.com/tirth8205/code-review-graph) — token-efficient code-graph MCP server (already wired into this workspace).
- [`ecc`](https://github.com/affaan-m/ecc) — the "SuperClaude"-style agent-harness framework whose plugin layout (`agents/`, `skills/`, `hooks/`, `commands/`, `.claude-plugin/`) this repo mirrors.
- `claurst` — a clean-room Rust reimplementation of Claude Code, whose `spec/`
  documents the internal **Undercover Mode** that this plugin re-creates.

> ⚠️ **Learning artifact.** This re-implements *publicly documented behaviour*
> from a leak analysis. It scrubs your own outgoing commit/PR text so it doesn't
> leak internal names or AI attribution. It is **not** a tool for evading code
> review or hiding wrongdoing — use it to practice writing clean, human-sounding,
> attribution-free commits. Don't use it to deceive anyone who *requires* AI
> disclosure (employer / school / client).

## Make commits NOT show "by AI" (the main use case)

Two layers, both inside sentinel-suite:

**1. The official switch (does the real work).** `sentinel-suite/.claude/settings.json`
sets:
```json
{ "includeCoAuthoredBy": false }
```
This is Claude Code's supported setting that stops the `Co-Authored-By: Claude`
trailer **and** the "Generated with Claude Code" line from being added to your
commits and PRs. With it off, Claude Code commits look like ordinary human
commits. (It applies when Claude Code runs with sentinel-suite as the project; to
get it in every project, copy that one line into `~/.claude/settings.json`.)

**2. The undercover enforcement (backstop).** The hooks in the same
`settings.json` run `hook_inject.py` (tells the model "do not blow your cover")
and `hook_guard.py` (a PreToolUse hook that **blocks** any `git commit` / `gh pr`
whose text still contains AI attribution or internal info, and suggests a clean
version).

So: setting #1 prevents the attribution being added; #2 catches it if it ever
sneaks back in. Together your Claude Code commits won't show that an AI made them.

See the live walkthrough in [`demo/demo.py`](demo/demo.py): `python demo/demo.py`.

## What's inside

```
sentinel-suite/
├── .claude-plugin/plugin.json   # plugin manifest
├── agents/undercover.md         # the "undercover" subagent
├── skills/undercover/SKILL.md   # invokable skill + docs
├── commands/undercover.md       # /undercover slash command
├── hooks/hooks.json             # wires the Python hooks into events
├── scripts/
│   ├── undercover.py            # core library + CLI (activation, scan, redact)
│   ├── hook_inject.py           # SessionStart/UserPromptSubmit -> inject prompt
│   └── hook_guard.py            # PreToolUse -> block cover-blowing git/gh cmds
└── tests/test_undercover.py
```

## The undercover agent — what it does

A faithful re-creation of Claude Code's `isUndercover()` + system-prompt
injection + enforcement, in pure-stdlib Python:

1. **Activation** (`is_undercover`): `CLAUDE_CODE_UNDERCOVER=1` forces ON;
   requires `USER_TYPE=ant` (defaults to `ant` here so it's demonstrable);
   otherwise automatic — ON unless the git remote is internal; **no force-OFF**.
2. **Prompt injection**: the `## UNDERCOVER MODE - CRITICAL … do not blow your
   cover` block, injected via the SessionStart / UserPromptSubmit hooks.
3. **Detection + redaction**: codenames (Tengu, Capybara…), unreleased versions
   (opus-4-7…), internal repo/tooling/Slack/`go/` links, `*.ant.dev` domains,
   the phrase "Claude Code", AI admissions, and `Co-Authored-By` attribution.
4. **Enforcement**: a PreToolUse hook denies `git commit` / `gh pr create` /
   `git tag` etc. whose text would blow the cover, with a redacted suggestion.

## Try it (no install needed)

```bash
cd sentinel-suite

python scripts/undercover.py status
python scripts/undercover.py prompt
python scripts/undercover.py scan --text "speed up tengu on opus-4-8, Co-Authored-By: Claude"
echo "Fix cache race" | python scripts/undercover.py scan -f -
python scripts/undercover.py redact --text "ship tengu (Generated with Claude Code)"

python tests/test_undercover.py        # or: python -m pytest tests/
```

## Use it as a Claude Code plugin

Add this folder as a plugin (e.g. via a local marketplace or
`--plugin-dir`), then in a session:

- `/undercover status` — see whether you're undercover and why.
- The `undercover` **skill** triggers on "scrub commit", "redact PR", etc.
- The `undercover` **agent** can be delegated commit/PR authoring.
- The hooks run automatically: the prompt block is injected each turn, and
  cover-blowing `git commit`/PR commands are blocked before they run.

## Customising the wordlist

Create `.undercover.json` in your repo root:

```json
{ "terms": ["projectatlas", "bluefin"] }
```

These get added to the codename detector for both `scan` and `redact`.

## Optional plain-git hook

```bash
# .git/hooks/commit-msg  (chmod +x)
python /abs/path/sentinel-suite/scripts/undercover.py check-commit "$1"
```
```
License: MIT
```
