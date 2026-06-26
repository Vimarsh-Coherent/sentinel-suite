"""Capability layer for the Sentinel Suite MCP server.

Pure functions (no MCP wiring) so they can be unit-tested directly. The MCP
server in ``server.py`` is a thin wrapper around these.

Paths are resolved relative to the Sentinel Suite repo root, discovered as:
  1. the ``SENTINEL_SUITE_ROOT`` environment variable, if set; else
  2. four parents up from this file (mcp-server/src/sentinel_suite_mcp/..).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional


def repo_root() -> Path:
    env = os.environ.get("SENTINEL_SUITE_ROOT")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[3]


def _ecc() -> Path:
    return repo_root() / "vendor" / "ecc"


# ---------------------------------------------------------------------------
# Guardrail (undercover) — reuse the in-repo undercover engine
# ---------------------------------------------------------------------------

def _load_undercover():
    scripts = repo_root() / "plugins" / "undercover" / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import undercover  # type: ignore
    return undercover


def guardrail_scan(text: str) -> list[dict]:
    uc = _load_undercover()
    rules = uc.build_rules(uc.load_extra_terms(str(repo_root())))
    return [f.to_dict() for f in uc.scan(text, rules)]


def guardrail_redact(text: str) -> str:
    uc = _load_undercover()
    rules = uc.build_rules(uc.load_extra_terms(str(repo_root())))
    return uc.redact(text, rules)


def guardrail_status() -> dict:
    uc = _load_undercover()
    d = uc.is_undercover(cwd=str(repo_root()))
    return {"active": d.active, "reason": d.reason}


# ---------------------------------------------------------------------------
# ECC skills & agents
# ---------------------------------------------------------------------------

def _frontmatter(text: str) -> dict:
    """Tiny front-matter parser: returns top-level key->value from a --- block."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    block = text[3:end]
    out: dict[str, str] = {}
    for line in block.splitlines():
        if ":" in line and not line.startswith(" "):
            k, _, v = line.partition(":")
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def ecc_list_skills(query: str = "") -> list[dict]:
    base = _ecc() / "skills"
    if not base.is_dir():
        return []
    q = query.lower()
    out: list[dict] = []
    for d in sorted(base.iterdir()):
        sk = d / "SKILL.md"
        if not sk.is_file():
            continue
        fm = _frontmatter(sk.read_text(encoding="utf-8", errors="ignore"))
        name = fm.get("name", d.name)
        desc = fm.get("description", "")
        if q and q not in name.lower() and q not in desc.lower():
            continue
        out.append({"name": name, "description": desc})
    return out


def ecc_get_skill(name: str) -> str:
    sk = _ecc() / "skills" / name / "SKILL.md"
    if not sk.is_file():
        return f"skill not found: {name}"
    return sk.read_text(encoding="utf-8", errors="ignore")


def ecc_list_agents(query: str = "") -> list[dict]:
    base = _ecc() / "agents"
    if not base.is_dir():
        return []
    q = query.lower()
    out: list[dict] = []
    for f in sorted(base.glob("*.md")):
        fm = _frontmatter(f.read_text(encoding="utf-8", errors="ignore"))
        name = fm.get("name", f.stem)
        desc = fm.get("description", "")
        if q and q not in name.lower() and q not in desc.lower():
            continue
        out.append({"name": name, "description": desc})
    return out


def ecc_get_agent(name: str) -> str:
    f = _ecc() / "agents" / (name if name.endswith(".md") else f"{name}.md")
    if not f.is_file():
        return f"agent not found: {name}"
    return f.read_text(encoding="utf-8", errors="ignore")


# ---------------------------------------------------------------------------
# Code graph (proxy to the code-review-graph CLI, if installed)
# ---------------------------------------------------------------------------

_CODE_GRAPH_ALLOWED = {"status", "build", "update"}


def code_graph(command: str = "status", cwd: Optional[str] = None) -> str:
    if command not in _CODE_GRAPH_ALLOWED:
        return f"command must be one of {sorted(_CODE_GRAPH_ALLOWED)}"
    try:
        out = subprocess.run(
            ["code-review-graph", command],
            capture_output=True, text=True, timeout=120, cwd=cwd or str(repo_root()),
        )
    except FileNotFoundError:
        return ("code-review-graph CLI not installed. Install with "
                "`pip install code-review-graph` (or `uvx code-review-graph`).")
    except Exception as e:  # pragma: no cover
        return f"error: {e}"
    return (out.stdout or "") + (out.stderr or "")


# ---------------------------------------------------------------------------
# Orchestrator (Octogent tentacles)
# ---------------------------------------------------------------------------

def create_tentacle(name: str, scope: str = "", cwd: Optional[str] = None) -> str:
    safe = "".join(c for c in name if c.isalnum() or c in "-_").strip("-_") or "tentacle"
    base = Path(cwd or os.getcwd()) / ".octogent" / "tentacles" / safe
    base.mkdir(parents=True, exist_ok=True)
    context = (
        f"# Tentacle: {safe}\n\n"
        f"## Scope\n{scope or 'Describe the slice of work this tentacle owns.'}\n\n"
        "## Sentinel Suite capabilities to use\n"
        "- Before any commit/PR: run the `guardrail_scan` tool to avoid leaking secrets/internal info.\n"
        "- For impact/architecture questions: use `code_graph`.\n"
        "- For ready-made workflows: search `ecc_list_skills` / `ecc_list_agents`.\n"
    )
    todo = f"# Todo — {safe}\n\n- [ ] First task for this tentacle\n"
    (base / "CONTEXT.md").write_text(context, encoding="utf-8")
    (base / "todo.md").write_text(todo, encoding="utf-8")
    return f"created tentacle '{safe}' at {base}"


def octogent_launch_command() -> str:
    launcher = repo_root() / "plugins" / "orchestrator" / "scripts" / "launch_octogent.py"
    return (
        f"Run: python \"{launcher}\"\n"
        "Needs Node >= 22 and pnpm. The dashboard opens at http://localhost:8787.\n"
        "(Long-running — start it in your own terminal, not via this tool.)"
    )


# ---------------------------------------------------------------------------
# Meta
# ---------------------------------------------------------------------------

def info() -> dict:
    return {
        "name": "sentinel-suite",
        "repo_root": str(repo_root()),
        "capabilities": {
            "Sentinel Suite Guard": "scan / redact / status",
            "Sentinel Suite Skills": f"{len(ecc_list_skills())} skills, {len(ecc_list_agents())} agents (powered by ecc)",
            "Sentinel Suite Graph": "status / build / update (powered by code-review-graph)",
            "Sentinel Suite Orchestrator": "create tentacles, launch dashboard (powered by Octogent)",
        },
    }
