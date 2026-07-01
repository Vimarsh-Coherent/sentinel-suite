# Sentinel Suite

> One toolkit for serious Claude Code work — a guardrail, code intelligence, a
> huge skills library, and multi-agent orchestration, all connectable through a
> single MCP server.

Sentinel Suite packages four capabilities under one roof and one brand:

| Sentinel Suite module | What it does | Powered by |
|---------------------|--------------|------------|
| **Sentinel Suite Guard** | Keeps secrets, internal codenames, unreleased versions, and AI attribution out of commits/PRs | original |
| **Sentinel Suite Graph** | Token-efficient, graph-based code intelligence (impact radius, architecture, hubs/bridges, semantic search) | [code-review-graph](https://github.com/tirth8205/code-review-graph) (MIT) |
| **Sentinel Suite Skills** | 67 agents · 271 skills · 92 commands for TDD, security, review, languages | [ecc](https://github.com/affaan-m/ecc) (MIT) |
| **Sentinel Suite Orchestrator** | Run many Claude Code sessions in parallel as scoped "tentacles" (tentacles + sessions + local dashboard) | original — pure-Python port of [Octogent](https://github.com/hesamsheikh/octogent)'s core (MIT) |
| **Sentinel Suite MCP** | One MCP server exposing all of the above as tools | original |

> Sentinel Suite is the unified surface. The "Powered by" projects are bundled
> under `vendor/` with their original licenses and authorship preserved — see
> [NOTICE.md](NOTICE.md). Sentinel Suite is the brand for the integrated toolkit,
> not a claim of authorship over those upstream projects.

## Layout

```
sentinel-suite/
├── .claude-plugin/marketplace.json   # the Sentinel Suite plugin marketplace
├── mcp-server/                       # Sentinel Suite MCP (unified server)
├── plugins/
│   ├── undercover/    → sentinel-guard
│   ├── code-graph/    → sentinel-graph
│   └── orchestrator/  → sentinel-orchestrator
├── vendor/                           # bundled upstream projects (MIT, attributed)
│   ├── ecc/           → sentinel-skills
│   ├── code-review-graph/            # powers Sentinel Suite Graph
│   └── octogent/                     # powers Sentinel Suite Orchestrator
├── README.md
└── NOTICE.md
```

## Two ways to use Sentinel Suite on your projects

### 1. Connect via the Sentinel Suite MCP server (recommended)

One server, every capability, from any MCP client (Claude Code, Cursor, …).

```bash
cd mcp-server && pip install -e .
```
```json
{ "mcpServers": { "sentinel-suite": {
    "command": "sentinel-suite-mcp",
    "env": { "SENTINEL_SUITE_ROOT": "/abs/path/to/sentinel-suite" },
    "type": "stdio" } } }
```
Remote/HTTP: `sentinel-suite-mcp --http --host 0.0.0.0 --port 8000`.
Tools: `guardrail_scan/redact/status`, `ecc_list_skills/get_skill`,
`ecc_list_agents/get_agent`, `code_graph`, `create_tentacle`,
`octogent_launch_command`, `sentinel_suite_info`. Details:
[mcp-server/README.md](mcp-server/README.md).

### 2. Install the Sentinel Suite plugins (native Claude Code)

```
/plugin marketplace add /abs/path/to/sentinel-suite
/plugin install sentinel-guard@sentinel-suite
/plugin install sentinel-graph@sentinel-suite
/plugin install sentinel-skills@sentinel-suite
/plugin install sentinel-orchestrator@sentinel-suite
```

## Requirements

- **Python 3.10+** — Guard, MCP server, **and the Orchestrator** (now pure Python — no Node needed).
- **`uv`/`uvx`** — optional, for Sentinel Suite Graph (`code-review-graph` server).

### Orchestrator (pure Python)
```bash
sentinel-suite orchestrate serve            # dashboard + API at http://127.0.0.1:8787
sentinel-suite orchestrate new frontend --scope "UI work"
sentinel-suite orchestrate run frontend "claude -p 'add tests'"
sentinel-suite orchestrate sessions
```

## License & attribution

Sentinel Suite's original parts (Guard, MCP server, plugin glue, marketplace) are
MIT. Bundled upstream projects keep their own MIT licenses and authorship — full
credits in [NOTICE.md](NOTICE.md).
