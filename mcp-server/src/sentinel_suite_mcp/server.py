"""Sentinel Suite unified MCP server (FastMCP).

Exposes the whole Sentinel Suite toolkit over the Model Context Protocol so any
MCP client (Claude Code, Cursor, Windsurf, Zed, ...) can connect and use:

  - guardrail_*   : scan / redact / status (the undercover engine)
  - ecc_*         : list & fetch the 271 ecc skills and 67 agents
  - code_graph    : status / build / update via the code-review-graph CLI
  - tentacle/octogent : scaffold Octogent tentacles, get the launch command
  - sentinel_suite_info : overview

Transports:
  - stdio (default)  : `sentinel-suite-mcp`            (for local MCP clients)
  - http             : `sentinel-suite-mcp --http`     (streamable-http, remote)
"""

from __future__ import annotations

import argparse
import sys

from mcp.server.fastmcp import FastMCP

from . import capabilities as cap

mcp = FastMCP("sentinel-suite")


# ---- guardrail (undercover) -------------------------------------------------

@mcp.tool()
def guardrail_scan(text: str) -> list[dict]:
    """Scan text for secrets, internal codenames, unreleased versions, and AI
    attribution that should not be committed. Returns a list of findings."""
    return cap.guardrail_scan(text)


@mcp.tool()
def guardrail_redact(text: str) -> str:
    """Return the text with secrets/sensitive content scrubbed and attribution
    lines removed. Use before writing a commit message or PR body."""
    return cap.guardrail_redact(text)


@mcp.tool()
def guardrail_status() -> dict:
    """Report whether undercover/guardrail mode is active for the current repo
    and why."""
    return cap.guardrail_status()


# ---- ecc knowledge ----------------------------------------------------------

@mcp.tool()
def ecc_list_skills(query: str = "") -> list[dict]:
    """List ecc skills (name + description). Optional case-insensitive `query`
    filters by name/description."""
    return cap.ecc_list_skills(query)


@mcp.tool()
def ecc_get_skill(name: str) -> str:
    """Return the full SKILL.md content for an ecc skill by name."""
    return cap.ecc_get_skill(name)


@mcp.tool()
def ecc_list_agents(query: str = "") -> list[dict]:
    """List ecc agents (name + description). Optional `query` filters."""
    return cap.ecc_list_agents(query)


@mcp.tool()
def ecc_get_agent(name: str) -> str:
    """Return the full markdown for an ecc agent by name."""
    return cap.ecc_get_agent(name)


# ---- code graph -------------------------------------------------------------

@mcp.tool()
def code_graph(command: str = "status") -> str:
    """Run the code-review-graph CLI. `command` is one of: status, build,
    update. Returns the CLI output."""
    return cap.code_graph(command)


# ---- orchestrator (octogent) ------------------------------------------------

@mcp.tool()
def create_tentacle(name: str, scope: str = "") -> str:
    """Scaffold an Octogent tentacle (.octogent/tentacles/<name>/ with
    CONTEXT.md + todo.md) wired to the Sentinel Suite capabilities."""
    return cap.create_tentacle(name, scope)


@mcp.tool()
def octogent_launch_command() -> str:
    """Return the command to launch the orchestrator dashboard (long-running; run
    it in your own terminal)."""
    return cap.octogent_launch_command()


@mcp.tool()
def orchestrate_send(sender: str, recipient: str, body: str, subject: str = "") -> dict:
    """Send an inter-agent message to a tentacle (or 'all' to broadcast). Use this
    to coordinate between parallel sessions."""
    return cap.orchestrate_send(sender, recipient, body, subject)


@mcp.tool()
def orchestrate_inbox(recipient: str, unread_only: bool = False) -> list[dict]:
    """Read inter-agent messages addressed to a tentacle (plus broadcasts)."""
    return cap.orchestrate_inbox(recipient, unread_only)


# ---- router + skill authoring ----------------------------------------------

@mcp.tool()
def recommend_for_prompt(prompt: str, kind: str = "both", top: int = 5,
                         method: str = "tfidf") -> dict:
    """Given a natural-language task, return the best-matching ecc agents and/or
    skills (kind = both | agents | skills). method = "tfidf" (semantic keyword
    ranking, default) or "embed" (true embeddings if installed). Use this to
    auto-pick which agent to delegate to or which skill to apply."""
    return cap.recommend(prompt, kind, top, method)


@mcp.tool()
def create_skill(name: str, description: str, instructions: str = "") -> dict:
    """Create a new skill file at ./.claude/skills/<name>/SKILL.md so it becomes
    available to Claude Code."""
    return cap.create_skill(name, description, instructions)


# ---- meta -------------------------------------------------------------------

@mcp.tool()
def sentinel_suite_info() -> dict:
    """Overview of the Sentinel Suite toolkit and its capability counts."""
    return cap.info()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sentinel-suite-mcp", description=__doc__.split("\n")[0])
    parser.add_argument("--http", action="store_true",
                        help="serve over streamable-http instead of stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)

    if args.http:
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        mcp.run(transport="streamable-http")
    else:
        mcp.run()  # stdio
    return 0


if __name__ == "__main__":
    sys.exit(main())
