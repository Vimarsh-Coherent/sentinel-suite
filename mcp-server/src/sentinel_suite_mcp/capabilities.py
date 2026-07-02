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
from pathlib import Path
from typing import Optional


def repo_root() -> Optional[Path]:
    """The Sentinel Suite repo checkout, if available.

    Resolves the SENTINEL_SUITE_ROOT env var, else four parents up from this
    file (works in an editable install inside the repo). Returns None when the
    package is pip-installed standalone and no checkout is reachable — callers
    then degrade gracefully.
    """
    env = os.environ.get("SENTINEL_SUITE_ROOT")
    if env and Path(env).is_dir():
        return Path(env)
    guess = Path(__file__).resolve().parents[3]
    return guess if (guess / "vendor").is_dir() or (guess / "plugins").is_dir() else None


_NO_REPO = ("This needs the full Sentinel Suite checkout. Clone it and set "
            "SENTINEL_SUITE_ROOT, e.g.:\n"
            "  git clone https://github.com/Vimarsh-Coherent/sentinel-suite\n"
            "  export SENTINEL_SUITE_ROOT=/path/to/sentinel-suite")


def _ecc() -> Optional[Path]:
    # Prefer a full checkout; otherwise use the ecc skills/agents bundled into
    # the wheel (so a plain `pip install` ships the whole library).
    root = repo_root()
    if root and (root / "vendor" / "ecc").is_dir():
        return root / "vendor" / "ecc"
    bundled = Path(__file__).resolve().parent / "_data" / "ecc"
    return bundled if bundled.is_dir() else None


# ---------------------------------------------------------------------------
# Guardrail (undercover) — bundled engine, works with zero checkout
# ---------------------------------------------------------------------------

def _load_undercover():
    # The guard engine is bundled in the package (_guard.py) so the guardrail
    # tools work even when pip-installed standalone.
    from . import _guard  # type: ignore
    return _guard


def _extra_terms_dir() -> str:
    # Look for an optional .undercover.json wordlist in the user's cwd.
    return os.getcwd()


def guardrail_scan(text: str) -> list[dict]:
    uc = _load_undercover()
    rules = uc.build_rules(uc.load_extra_terms(_extra_terms_dir()))
    return [f.to_dict() for f in uc.scan(text, rules)]


def guardrail_redact(text: str) -> str:
    uc = _load_undercover()
    rules = uc.build_rules(uc.load_extra_terms(_extra_terms_dir()))
    return uc.redact(text, rules)


def guardrail_status() -> dict:
    uc = _load_undercover()
    d = uc.is_undercover(cwd=os.getcwd())
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
    ecc = _ecc()
    if ecc is None:
        return [{"name": "(unavailable)", "description": _NO_REPO}]
    base = ecc / "skills"
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
    ecc = _ecc()
    if ecc is None:
        return _NO_REPO
    sk = ecc / "skills" / name / "SKILL.md"
    if not sk.is_file():
        return f"skill not found: {name}"
    return sk.read_text(encoding="utf-8", errors="ignore")


def ecc_list_agents(query: str = "") -> list[dict]:
    ecc = _ecc()
    if ecc is None:
        return [{"name": "(unavailable)", "description": _NO_REPO}]
    base = ecc / "agents"
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
    ecc = _ecc()
    if ecc is None:
        return _NO_REPO
    f = ecc / "agents" / (name if name.endswith(".md") else f"{name}.md")
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
            capture_output=True, text=True, timeout=120, cwd=cwd or os.getcwd(),
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


def orchestrate_send(sender: str, recipient: str, body: str, subject: str = "",
                     cwd: Optional[str] = None) -> dict:
    from .orchestrator import Orchestrator
    m = Orchestrator(cwd or os.getcwd()).send_message(sender, recipient, body, subject)
    return m.__dict__


def orchestrate_inbox(recipient: str, unread_only: bool = False,
                      cwd: Optional[str] = None) -> list[dict]:
    from .orchestrator import Orchestrator
    return [m.__dict__ for m in Orchestrator(cwd or os.getcwd()).inbox(recipient, unread_only)]


def octogent_launch_command() -> str:
    # The orchestrator is now a pure-Python port — no Node needed.
    return (
        "Sentinel Suite Orchestrator (pure Python — no Node required):\n"
        "  sentinel-suite orchestrate serve     # dashboard + API at http://127.0.0.1:8787\n"
        "  sentinel-suite orchestrate new <name>    # create a tentacle\n"
        "  sentinel-suite orchestrate run <tentacle> <command...>   # start a session\n"
        "  sentinel-suite orchestrate sessions  # list sessions\n"
        "(Start `serve` in your own terminal — it's long-running.)"
    )


# ---------------------------------------------------------------------------
# Meta
# ---------------------------------------------------------------------------

def info() -> dict:
    root = repo_root()
    skills = ecc_list_skills()
    have_ecc = not (skills and skills[0].get("name") == "(unavailable)")
    n_skills = len(skills) if have_ecc else 0
    return {
        "name": "sentinel-suite",
        "repo_root": str(root) if root else None,
        "mode": "full checkout" if root else "pip install (everything Python; ecc bundled)",
        "capabilities": {
            "Sentinel Suite Guard": "scan / redact / status (always available)",
            "Sentinel Suite Skills": (f"{n_skills} skills, {len(ecc_list_agents())} agents"
                                      if have_ecc else "unavailable"),
            "Sentinel Suite Graph": "status / build / update (needs code-review-graph CLI)",
            "Sentinel Suite Orchestrator": "tentacles + sessions + dashboard (pure Python, no Node)",
        },
    }
