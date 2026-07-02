# Sentinel Suite

**A toolkit that makes your AI coding assistant safer and smarter — install once, works across Claude Code, Cursor, Windsurf, and Zed.**

Type a normal prompt and Sentinel Suite automatically picks the right expert agent and skill, keeps your commits clean, understands your codebase, and can run a whole team of AI workers in parallel — all from one install.

```bash
pip install "git+https://github.com/Vimarsh-Coherent/sentinel-suite"
sentinel-suite setup            # wire it into the current project
sentinel-suite connect --target cursor   # (or windsurf | zed | claude | all)
```

---

## What you get

### 🛡️ Guard — clean, safe commits
Scans commit messages and PR text before they leave your machine and blocks anything that shouldn't ship: **API keys, tokens, private keys, credit-card numbers, and AI-attribution lines**. Works as a git hook, a command, and an MCP tool.

### 🧭 Router — just type, it picks the right agent + skill
On every prompt, a semantic router matches your request against **286 skills and 67 agents** and tells you which it's using (you can override). "Add OAuth login" → `auth-oauth-jwt` skill; "my queries are slow" → `database-query-optimization` + `database-reviewer`.

### 📚 Skills & Agents — a ready-made expert library
**286 skills** (TDD, security, CI/CD, GraphQL, microservices, observability, refactoring, and more) and **67 agents** (architect, code-reviewer, security-auditor, language experts). List them, view them, install them into your project, or create your own.

### 🕸️ Graph — automatic code intelligence
Builds a knowledge graph of your codebase and **keeps it updated automatically** (rebuilds on session start, updates after every edit). Answers "what breaks if I change this?", architecture overviews, and impact analysis — without you asking.

### 🐙 Orchestrator — a team of AI workers that talk to each other
Run many tasks in parallel as scoped **tentacles**. A **coordinator** assigns work; **workers** pick it up automatically (auto-inbox) and message results back. Watch it all live in a browser dashboard.

---

## Quick start

```bash
# 1. install
pip install "git+https://github.com/Vimarsh-Coherent/sentinel-suite"

# 2. set it up in your project (guard + skills/agents + auto-graph + auto-router)
cd your-project
sentinel-suite setup

# 3. connect it to your editor
sentinel-suite connect --target cursor      # claude | cursor | windsurf | zed | all
```
Restart your editor — now just talk to it normally.

---

## Command cheat sheet

| Command | What it does |
|---------|-------------|
| `sentinel-suite setup` | wire everything into the current project |
| `sentinel-suite connect --target <tool>` | add Sentinel Suite to Cursor / Windsurf / Zed / Claude |
| `sentinel-suite recommend "<prompt>"` | show the best agent + skill for a task |
| `sentinel-suite scan --text "…"` | check text for secrets / leaks |
| `sentinel-suite agents` / `skills` | browse the library |
| `sentinel-suite skill-new "<name>"` | create your own skill |
| `sentinel-suite orchestrate team frontend backend docs` | start a coordinator + workers |
| `sentinel-suite orchestrate serve` | open the live team dashboard (:8787) |
| `sentinel-suite orchestrate send coordinator frontend "do X"` | assign / message a worker |
| `sentinel-suite orchestrate stop-all` | tear the team down |
| `sentinel-suite-mcp` | run the MCP server (used by your editor) |

---

## How it works

```
your prompt
   │
   ▼
Router ──picks──▶ best agent + skill   (from 286 skills / 67 agents)
   │
Graph ──gives──▶ code intelligence     (auto-built, always fresh)
   │
Guard ──checks─▶ commits & PRs         (no secrets / no AI attribution)
   │
Orchestrator ──runs──▶ parallel workers that message each other
   │
All exposed through one MCP server → works in any MCP-capable editor.
```

---

## Connect to your editor

`sentinel-suite connect --target <tool>` writes the right MCP config **and** an
always-on rule so the assistant uses the router + guard automatically:

| Tool | Files written |
|------|---------------|
| Cursor | `.cursor/mcp.json`, `.cursor/rules/sentinel-suite.mdc` |
| Windsurf | `.windsurf/mcp.json`, `.windsurf/rules/sentinel-suite.md` |
| Zed | `.zed/sentinel-suite.mcp.json`, `.zed/sentinel-suite.rules.md` |
| Claude Code | `.mcp.json` (+ `sentinel-suite setup` for full hooks) |

---

## Requirements

- **Python 3.10+** — the whole toolkit runs on Python (no Node required).
- **`uv`** *(optional)* — for the code graph engine.
- **`sentence-transformers`** *(optional)* — for embedding-based routing (`recommend --embed`). The default router needs nothing extra.

---

## Try it in 30 seconds

```bash
sentinel-suite recommend "review my code for security issues"
sentinel-suite scan --text "deploy with key AKIAABCDEFGHIJKLMNOP"
sentinel-suite orchestrate team frontend backend
sentinel-suite orchestrate serve      # http://127.0.0.1:8787
```

---

*Credits: Sentinel Suite bundles and builds on `ecc`, `code-review-graph`, and `Octogent` — see [NOTICE.md](NOTICE.md).*
