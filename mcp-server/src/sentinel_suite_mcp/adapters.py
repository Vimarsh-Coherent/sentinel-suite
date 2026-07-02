"""Multi-tool adapters — wire Sentinel Suite into any AI coding tool.

The engine is an MCP server + CLI, so it's tool-agnostic. Each tool just needs
(1) its MCP config pointing at `sentinel-suite-mcp`, and (2) a "rules" file that
tells the agent to use the router + guard. These adapters write both in the
right place/format for each tool.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

# The behaviour we want every tool to follow (its "always-on" instructions).
RULE_BODY = (
    "For every coding task in this project, use Sentinel Suite via its MCP tools:\n\n"
    "1. Call `recommend_for_prompt` with the user's request, then briefly tell the "
    "user which agent/skill you'll use (they can say 'no' to skip).\n"
    "2. For impact/architecture questions, use the `code_graph` tool.\n"
    "3. Before committing or opening a PR, call `guardrail_scan` on the commit/PR "
    "text and remove any findings (secrets, AI attribution, internal info).\n"
    "4. For big multi-part work, use the `orchestrate_*` tools (tentacles + messaging).\n"
)


def _server(root: Optional[str]) -> dict:
    s: dict = {"command": "sentinel-suite-mcp", "args": [], "type": "stdio"}
    if root:
        s["env"] = {"SENTINEL_SUITE_ROOT": root}
    return s


def _merge_mcp(path: Path, root: Optional[str]) -> None:
    data: dict = {}
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8") or "{}")
        except json.JSONDecodeError:
            data = {}
    data.setdefault("mcpServers", {})["sentinel-suite"] = _server(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Per-tool adapters — each returns a list of files written + notes
# ---------------------------------------------------------------------------

def install_cursor(base: Path, root: Optional[str]) -> list:
    out = []
    _merge_mcp(base / ".cursor" / "mcp.json", root)
    out.append(".cursor/mcp.json (MCP server)")
    # Cursor rules use MDC with frontmatter; alwaysApply injects it every task.
    mdc = ("---\ndescription: Sentinel Suite — auto-route to the best agent/skill "
           "and guard commits\nalwaysApply: true\n---\n\n# Sentinel Suite\n\n" + RULE_BODY)
    _write(base / ".cursor" / "rules" / "sentinel-suite.mdc", mdc)
    out.append(".cursor/rules/sentinel-suite.mdc (always-on rule)")
    return out


def install_windsurf(base: Path, root: Optional[str]) -> list:
    out = []
    _merge_mcp(base / ".windsurf" / "mcp.json", root)
    out.append(".windsurf/mcp.json (MCP server — copy into Windsurf's MCP config)")
    _write(base / ".windsurf" / "rules" / "sentinel-suite.md", "# Sentinel Suite\n\n" + RULE_BODY)
    out.append(".windsurf/rules/sentinel-suite.md (always-on rule)")
    return out


def install_zed(base: Path, root: Optional[str]) -> list:
    out = []
    # Zed configures MCP ("context servers") in settings.json — provide a snippet.
    snippet = {"context_servers": {"sentinel-suite": {"command": {"path": "sentinel-suite-mcp", "args": []}}}}
    _write(base / ".zed" / "sentinel-suite.mcp.json", json.dumps(snippet, indent=2) + "\n")
    out.append(".zed/sentinel-suite.mcp.json (snippet for Zed settings.json)")
    _write(base / ".zed" / "sentinel-suite.rules.md", "# Sentinel Suite\n\n" + RULE_BODY)
    out.append(".zed/sentinel-suite.rules.md (paste into your Zed rules)")
    return out


def install_claude(base: Path, root: Optional[str]) -> list:
    out = []
    _merge_mcp(base / ".mcp.json", root)
    out.append(".mcp.json (MCP server)")
    out.append("note: run `sentinel-suite setup` for the full auto experience "
               "(hooks: auto-router, auto-graph, commit guard)")
    return out


ADAPTERS = {
    "claude": install_claude,
    "cursor": install_cursor,
    "windsurf": install_windsurf,
    "zed": install_zed,
}


def connect(target: str, cwd: Optional[str] = None, root: Optional[str] = None) -> dict:
    """Wire Sentinel Suite into one tool (or 'all'). Returns {tool: [files]}."""
    base = Path(cwd or os.getcwd())
    targets = list(ADAPTERS) if target == "all" else [target]
    result: dict = {}
    for t in targets:
        fn = ADAPTERS.get(t)
        if not fn:
            result[t] = [f"unknown target (choose from: {', '.join(ADAPTERS)} or all)"]
            continue
        result[t] = fn(base, root)
    return result
