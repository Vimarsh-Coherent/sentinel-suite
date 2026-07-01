# Sentinel Suite MCP server

A single **MCP server** that exposes the whole Sentinel Suite toolkit so any MCP
client (Claude Code, Cursor, Windsurf, Zed, Continue, …) can connect and use it.

## Tools exposed

| Tool | What it does |
|------|--------------|
| `guardrail_scan(text)` | find secrets / internal codenames / unreleased versions / AI attribution |
| `guardrail_redact(text)` | return a scrubbed version of the text |
| `guardrail_status()` | is undercover/guardrail mode active, and why |
| `ecc_list_skills(query?)` | list/search the vendored ecc skills (name + description) |
| `ecc_get_skill(name)` | fetch a skill's full `SKILL.md` |
| `ecc_list_agents(query?)` | list/search the ecc agents |
| `ecc_get_agent(name)` | fetch an agent's markdown |
| `code_graph(command)` | run `code-review-graph` (`status` / `build` / `update`) |
| `create_tentacle(name, scope?)` | scaffold an Octogent tentacle wired to these tools |
| `octogent_launch_command()` | get the command to launch the Octogent dashboard |
| `sentinel_suite_info()` | overview + capability counts |

## Install — one line (no clone needed)

One `pip install` ships the **guardrail**, the **full ecc library (271 skills +
67 agents, bundled into the wheel)**, and pulls **code-review-graph** as a
dependency. Everything pip can deliver, in one command.

**pip (one line):**
```bash
pip install "git+https://github.com/Vimarsh-Coherent/sentinel-suite"
```

**Connect MCP (auto-installs on connect via uvx — nothing to pip first):**
```json
{
  "mcpServers": {
    "sentinel-suite": {
      "command": "uvx",
      "args": ["--from",
               "git+https://github.com/Vimarsh-Coherent/sentinel-suite",
               "sentinel-suite-mcp"],
      "type": "stdio"
    }
  }
}
```
That's it — when your MCP client connects, `uvx` fetches and runs the server.
(Once published to PyPI, this shortens to `uvx sentinel-suite-mcp` /
`pip install sentinel-suite`.)

After install you also get a CLI:
```bash
sentinel-suite scan --text "ship tengu"     # guardrail
sentinel-suite init --global-hooks          # no AI attribution on commits, everywhere
sentinel-suite agents / skills              # list the 67 agents / 271 skills
sentinel-suite install-agents               # register agents into .claude/agents
sentinel-suite info                         # what's available

# Orchestrator — pure Python, no Node:
sentinel-suite orchestrate serve            # dashboard + API at http://127.0.0.1:8787
sentinel-suite orchestrate new frontend --scope "UI"
sentinel-suite orchestrate run frontend "claude -p 'add tests'"
sentinel-suite orchestrate sessions
```

**Everything now installs with pip** — the Orchestrator was ported from Node
(Octogent) to pure Python, so there are no non-Python requirements.

### Local dev install
```bash
cd sentinel-suite/mcp-server
pip install -e .          # or: uvx --from . sentinel-suite-mcp
```

## Connect from a client

The server resolves the Sentinel Suite repo via the `SENTINEL_SUITE_ROOT` env var
(falls back to its location inside the repo). Point it at your checkout.

**Claude Code / Cursor / Windsurf** — add to the client's MCP config
(`.mcp.json` or settings). Example (stdio):

```json
{
  "mcpServers": {
    "sentinel-suite": {
      "command": "sentinel-suite-mcp",
      "env": { "SENTINEL_SUITE_ROOT": "/abs/path/to/sentinel-suite" },
      "type": "stdio"
    }
  }
}
```

See [`examples/mcp.stdio.json`](examples/mcp.stdio.json) and
[`examples/mcp.uvx.json`](examples/mcp.uvx.json).

### Remote / HTTP

For a network-reachable server (so multiple machines can connect):

```bash
sentinel-suite-mcp --http --host 0.0.0.0 --port 8000
```

Then point an HTTP-capable MCP client at `http://<host>:8000/mcp`.

## Verify it

```bash
pip install -e ".[dev]"
pytest                                   # capability + tools-list tests
python -c "import asyncio; from sentinel_suite_mcp.server import mcp; print(len(asyncio.run(mcp.list_tools())), 'tools')"
```

## How it fits the repo

This server is the "connect to everything" front door for Sentinel Suite:

```
MCP client ──> sentinel-suite-mcp ──┬─ guardrail   (plugins/undercover engine)
                                  ├─ ecc         (vendor/ecc skills + agents)
                                  ├─ code_graph  (code-review-graph CLI)
                                  └─ orchestrator (Octogent tentacles)
```
