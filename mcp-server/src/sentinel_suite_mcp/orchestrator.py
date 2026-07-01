"""Sentinel Suite Orchestrator — a pure-Python port of Octogent's core.

Octogent (https://github.com/hesamsheikh/octogent, MIT) is a Node.js app that
orchestrates many Claude Code sessions. This module re-implements its **core
model** in pure stdlib Python so it works from a plain `pip install` — no Node:

  • Project scaffold  — a `.octogent/` dir (tentacles / sessions / worktrees),
    Octogent-compatible so the layouts interoperate.
  • Tentacles         — scoped job folders with CONTEXT.md + todo.md + meta.json
    (mirrors Octogent's `/api/deck/tentacles`).
  • Session runtime   — spawn/track/stop background sessions (e.g. `claude ...`),
    each logging to a file, with live status from PID liveness.
  • Local API + dashboard — a stdlib http.server exposing /api/tentacles and
    /api/sessions plus a single-page HTML dashboard (Octogent's :8787 role).

What is intentionally NOT ported: Octogent's rich TS/CSS web UI and interactive
PTY terminals. Sessions here are background processes logging to files (simple,
cross-platform), not live PTYs.
"""

from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Process liveness (cross-platform, zero deps)
# ---------------------------------------------------------------------------

def _pid_alive(pid: Optional[int]) -> bool:
    if not pid:
        return False
    if os.name == "nt":
        import ctypes
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        h = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not h:
            return False
        try:
            code = ctypes.c_ulong()
            ok = ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(code))
            return bool(ok) and code.value == STILL_ACTIVE
        finally:
            ctypes.windll.kernel32.CloseHandle(h)
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def _slug(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_-]+", "-", name).strip("-_").lower()
    return s or "item"


# ---------------------------------------------------------------------------
# Domain
# ---------------------------------------------------------------------------

@dataclass
class Tentacle:
    id: str
    description: str
    scope: str
    path: str
    created: float


@dataclass
class Session:
    id: str
    tentacle: str
    command: str
    pid: Optional[int]
    started: float
    log: str
    status: str = "running"


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class Orchestrator:
    """Manages a project's `.octogent/` scaffold, tentacles, and sessions."""

    def __init__(self, root: Optional[str] = None):
        self.root = Path(root or os.getcwd()).resolve()
        self.base = self.root / ".octogent"
        self.tentacles_dir = self.base / "tentacles"
        self.sessions_dir = self.base / "sessions"
        self.worktrees_dir = self.base / "worktrees"

    # ---- scaffold -------------------------------------------------------
    def scaffold(self) -> dict:
        for d in (self.tentacles_dir, self.sessions_dir, self.worktrees_dir):
            d.mkdir(parents=True, exist_ok=True)
        meta = self.base / "project.json"
        if not meta.is_file():
            meta.write_text(json.dumps(
                {"name": self.root.name, "created": self._now()}, indent=2), encoding="utf-8")
        gi = self.base / ".gitignore"
        if not gi.is_file():
            gi.write_text("sessions/\nworktrees/\n", encoding="utf-8")
        return {"scaffold": str(self.base), "project": self.root.name}

    @staticmethod
    def _now() -> float:
        # Wall-clock via os.stat of a temp write would be cleaner, but time.time
        # is fine here (orchestrator runs live, not in a replayed workflow).
        return time.time()

    # ---- tentacles ------------------------------------------------------
    def create_tentacle(self, name: str, description: str = "", scope: str = "") -> Tentacle:
        self.scaffold()
        tid = _slug(name)
        path = self.tentacles_dir / tid
        path.mkdir(parents=True, exist_ok=True)
        context = (
            f"# Tentacle: {tid}\n\n"
            f"## Scope\n{scope or 'Describe the slice of work this tentacle owns.'}\n\n"
            "## Sentinel Suite capabilities to use\n"
            "- Before any commit/PR: `guardrail_scan` (avoid leaking secrets/internal info).\n"
            "- For impact/architecture: `code_graph`.\n"
            "- For ready-made workflows: `ecc_list_skills` / `ecc_list_agents`.\n"
        )
        (path / "CONTEXT.md").write_text(context, encoding="utf-8")
        if not (path / "todo.md").is_file():
            (path / "todo.md").write_text(f"# Todo — {tid}\n\n- [ ] First task\n", encoding="utf-8")
        t = Tentacle(id=tid, description=description, scope=scope,
                     path=str(path), created=self._now())
        (path / "meta.json").write_text(json.dumps(asdict(t), indent=2), encoding="utf-8")
        return t

    def list_tentacles(self) -> list[Tentacle]:
        if not self.tentacles_dir.is_dir():
            return []
        out: list[Tentacle] = []
        for d in sorted(p for p in self.tentacles_dir.iterdir() if p.is_dir()):
            meta = d / "meta.json"
            if meta.is_file():
                try:
                    out.append(Tentacle(**json.loads(meta.read_text(encoding="utf-8"))))
                    continue
                except Exception:
                    pass
            out.append(Tentacle(id=d.name, description="", scope="", path=str(d), created=0.0))
        return out

    # ---- sessions -------------------------------------------------------
    def spawn_session(self, tentacle: str, command: str) -> Session:
        self.scaffold()
        tid = _slug(tentacle)
        cwd = self.tentacles_dir / tid
        cwd.mkdir(parents=True, exist_ok=True)
        sid = f"{tid}-{int(self._now())}"
        log = self.sessions_dir / f"{sid}.log"
        kwargs: dict = {}
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
        else:
            kwargs["start_new_session"] = True
        with open(log, "w", encoding="utf-8") as fh:
            proc = subprocess.Popen(command, shell=True, cwd=str(cwd),
                                    stdout=fh, stderr=subprocess.STDOUT, **kwargs)
        s = Session(id=sid, tentacle=tid, command=command, pid=proc.pid,
                    started=self._now(), log=str(log), status="running")
        (self.sessions_dir / f"{sid}.json").write_text(
            json.dumps(asdict(s), indent=2), encoding="utf-8")
        return s

    def list_sessions(self) -> list[Session]:
        if not self.sessions_dir.is_dir():
            return []
        out: list[Session] = []
        for f in sorted(self.sessions_dir.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            s = Session(**data)
            s.status = "running" if _pid_alive(s.pid) else "finished"
            out.append(s)
        return out

    def stop_session(self, session_id: str) -> dict:
        f = self.sessions_dir / f"{session_id}.json"
        if not f.is_file():
            return {"ok": False, "error": f"no such session: {session_id}"}
        s = Session(**json.loads(f.read_text(encoding="utf-8")))
        if s.pid and _pid_alive(s.pid):
            try:
                if os.name == "nt":
                    os.kill(s.pid, signal.SIGTERM)
                else:
                    os.killpg(os.getpgid(s.pid), signal.SIGTERM)
            except Exception as e:  # pragma: no cover
                return {"ok": False, "error": str(e)}
        return {"ok": True, "stopped": session_id}

    def summary(self) -> dict:
        return {
            "project": self.root.name,
            "root": str(self.root),
            "tentacles": [asdict(t) for t in self.list_tentacles()],
            "sessions": [asdict(s) for s in self.list_sessions()],
        }
