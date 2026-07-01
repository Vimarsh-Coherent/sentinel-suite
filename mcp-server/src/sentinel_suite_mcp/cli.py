"""Sentinel Suite unified CLI (`sentinel-suite`).

Available after `pip install sentinel-suite`, with no checkout needed:

    sentinel-suite scan   --text "..."     # find secrets / AI attribution / internal info
    sentinel-suite redact --text "..."     # print a cleaned version
    sentinel-suite status                  # is the guardrail active here, and why
    sentinel-suite init [--global-hooks]   # opt in: no AI attribution on commits/PRs
    sentinel-suite mcp                     # run the MCP server (stdio)
    sentinel-suite info                    # what's available in this install
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from . import _guard
from . import capabilities as cap


def _utf8() -> None:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except Exception:
            pass


def _rules():
    return _guard.build_rules(_guard.load_extra_terms(os.getcwd()))


def _text(a) -> str:
    return a.text if a.text is not None else sys.stdin.read()


def cmd_scan(a) -> int:
    findings = _guard.scan(_text(a), _rules())
    if a.json:
        print(json.dumps([f.to_dict() for f in findings], indent=2))
    elif not findings:
        print("✅ clean")
    else:
        print(f"⚠️  {len(findings)} finding(s):")
        for f in findings:
            print(f"  [{f.category}] {f.match!r} — {f.reason}")
    return 1 if findings else 0


def cmd_redact(a) -> int:
    sys.stdout.write(_guard.redact(_text(a), _rules()))
    return 0


def cmd_status(a) -> int:
    d = _guard.is_undercover(cwd=os.getcwd())
    print(json.dumps({"active": d.active, "reason": d.reason}, indent=2))
    return 0


def cmd_mcp(a) -> int:
    from .server import main as server_main
    return server_main([])


def cmd_agents(a) -> int:
    items = cap.ecc_list_agents(a.query or "")
    if a.json:
        print(json.dumps(items, indent=2))
    else:
        print(f"{len(items)} agent(s):")
        for it in items:
            print(f"  • {it['name']:<28} {it['description'][:70]}")
    return 0


def cmd_agent(a) -> int:
    print(cap.ecc_get_agent(a.name))
    return 0


def cmd_skills(a) -> int:
    items = cap.ecc_list_skills(a.query or "")
    if a.json:
        print(json.dumps(items, indent=2))
    else:
        print(f"{len(items)} skill(s):")
        for it in items:
            print(f"  • {it['name']:<28} {it['description'][:70]}")
    return 0


def cmd_skill(a) -> int:
    print(cap.ecc_get_skill(a.name))
    return 0


def _install_dir(kind: str, target: str | None) -> int:
    import shutil
    base = cap._ecc()
    if base is None:
        print(cap._NO_REPO, file=sys.stderr)
        return 2
    src = base / kind  # "agents" or "skills"
    if not src.is_dir():
        print(f"no {kind} found in the bundle", file=sys.stderr)
        return 2
    dst = Path(target) if target else (Path.cwd() / ".claude" / kind)
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    if kind == "agents":
        for f in sorted(src.glob("*.md")):
            shutil.copy2(f, dst / f.name)
            n += 1
    else:  # skills are folders
        for d in sorted(p for p in src.iterdir() if p.is_dir()):
            tgt = dst / d.name
            if tgt.exists():
                shutil.rmtree(tgt)
            shutil.copytree(d, tgt)
            n += 1
    print(f"✅ installed {n} {kind} -> {dst}")
    print(f"   Claude Code will pick them up from {dst} (restart the session).")
    return 0


def cmd_install_agents(a) -> int:
    return _install_dir("agents", a.dir)


def cmd_install_skills(a) -> int:
    return _install_dir("skills", a.dir)


# ---- orchestrator (Python port of Octogent) --------------------------------

def cmd_orch_serve(a) -> int:
    from .orchestrator_server import serve
    return serve(a.host, a.port, a.root)


def cmd_orch_new(a) -> int:
    from .orchestrator import Orchestrator
    t = Orchestrator(a.root).create_tentacle(a.name, a.desc or "", a.scope or "")
    print(f"✅ created tentacle '{t.id}' at {t.path}")
    return 0


def cmd_orch_ls(a) -> int:
    from .orchestrator import Orchestrator
    ts = Orchestrator(a.root).list_tentacles()
    if not ts:
        print("no tentacles yet (create one with: sentinel-suite orchestrate new <name>)")
    for t in ts:
        print(f"  • {t.id}" + (f" — {t.scope}" if t.scope else ""))
    return 0


def cmd_orch_run(a) -> int:
    from .orchestrator import Orchestrator
    s = Orchestrator(a.root).spawn_session(a.tentacle, " ".join(a.command))
    print(f"✅ started session '{s.id}' (pid {s.pid}); log: {s.log}")
    return 0


def cmd_orch_sessions(a) -> int:
    from .orchestrator import Orchestrator
    ss = Orchestrator(a.root).list_sessions()
    if not ss:
        print("no sessions yet")
    for s in ss:
        print(f"  • {s.id}  [{s.status}]  {s.command}")
    return 0


def cmd_orch_stop(a) -> int:
    from .orchestrator import Orchestrator
    r = Orchestrator(a.root).stop_session(a.session_id)
    print(("✅ " if r.get("ok") else "❌ ") + json.dumps(r))
    return 0 if r.get("ok") else 2


def cmd_info(a) -> int:
    print(json.dumps(cap.info(), indent=2))
    return 0


def cmd_init(a) -> int:
    # 1. official switch: no AI attribution on commits/PRs
    settings = Path.home() / ".claude" / "settings.json"
    data = {}
    if settings.is_file():
        try:
            data = json.loads(settings.read_text(encoding="utf-8") or "{}")
        except json.JSONDecodeError:
            print(f"⚠️  {settings} is not valid JSON; fix it first.", file=sys.stderr)
            return 2
    if data.get("includeCoAuthoredBy") is not False:
        data["includeCoAuthoredBy"] = False
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"✅ set includeCoAuthoredBy=false in {settings}")
    else:
        print(f"✅ already set: includeCoAuthoredBy=false in {settings}")

    # 2. optional: global git hooks that guard every repo on this machine
    if a.global_hooks:
        hooks_dir = Path.home() / ".sentinel-suite" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        guard = "python -m sentinel_suite_mcp._guard"
        (hooks_dir / "commit-msg").write_text(
            f'#!/bin/sh\n# Sentinel Suite\n{guard} check-commit "$1" || exit 1\n', encoding="utf-8")
        (hooks_dir / "pre-push").write_text(
            f'#!/bin/sh\n# Sentinel Suite\n{guard} check-push || exit 1\n', encoding="utf-8")
        for h in ("commit-msg", "pre-push"):
            try:
                (hooks_dir / h).chmod(0o755)
            except Exception:
                pass
        subprocess.run(["git", "config", "--global", "core.hooksPath", hooks_dir.as_posix()],
                       check=False)
        print(f"✅ global git hooks installed -> {hooks_dir.as_posix()}")
        print("   (commit & push are now guarded in every repo on this machine)")
    else:
        print("   (run `sentinel-suite init --global-hooks` to also guard every repo)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sentinel-suite", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    for name, fn in (("scan", cmd_scan), ("redact", cmd_redact)):
        sp = sub.add_parser(name)
        sp.add_argument("--text", default=None, help="text (default: stdin)")
        sp.add_argument("--json", action="store_true")
        sp.set_defaults(func=fn)

    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("info").set_defaults(func=cmd_info)
    sub.add_parser("mcp").set_defaults(func=cmd_mcp)

    # ecc agents / skills: list, view, and install into .claude/
    sp = sub.add_parser("agents", help="list the bundled ecc agents")
    sp.add_argument("query", nargs="?", default="")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_agents)

    sp = sub.add_parser("agent", help="print one agent's full definition")
    sp.add_argument("name")
    sp.set_defaults(func=cmd_agent)

    sp = sub.add_parser("skills", help="list the bundled ecc skills")
    sp.add_argument("query", nargs="?", default="")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_skills)

    sp = sub.add_parser("skill", help="print one skill's full definition")
    sp.add_argument("name")
    sp.set_defaults(func=cmd_skill)

    sp = sub.add_parser("install-agents", help="copy all agents into .claude/agents so Claude Code can use them")
    sp.add_argument("--dir", default=None, help="target dir (default: ./.claude/agents)")
    sp.set_defaults(func=cmd_install_agents)

    sp = sub.add_parser("install-skills", help="copy all skills into .claude/skills")
    sp.add_argument("--dir", default=None, help="target dir (default: ./.claude/skills)")
    sp.set_defaults(func=cmd_install_skills)

    sp = sub.add_parser("init", help="opt in: no AI attribution on commits/PRs")
    sp.add_argument("--global-hooks", action="store_true",
                    help="also guard every repo on this machine")
    sp.set_defaults(func=cmd_init)

    # orchestrator (pure-Python port of Octogent)
    orch = sub.add_parser("orchestrate", help="multi-session orchestrator (Python port of Octogent)")
    osub = orch.add_subparsers(dest="action", required=True)

    sp = osub.add_parser("serve", help="run the local API + dashboard (default :8787)")
    sp.add_argument("--host", default="127.0.0.1")
    sp.add_argument("--port", type=int, default=8787)
    sp.add_argument("--root", default=None)
    sp.set_defaults(func=cmd_orch_serve)

    sp = osub.add_parser("new", help="create a tentacle (scoped job folder)")
    sp.add_argument("name")
    sp.add_argument("--desc", default=None)
    sp.add_argument("--scope", default=None)
    sp.add_argument("--root", default=None)
    sp.set_defaults(func=cmd_orch_new)

    sp = osub.add_parser("ls", help="list tentacles")
    sp.add_argument("--root", default=None)
    sp.set_defaults(func=cmd_orch_ls)

    sp = osub.add_parser("run", help="start a background session in a tentacle")
    sp.add_argument("tentacle")
    sp.add_argument("command", nargs="+")
    sp.add_argument("--root", default=None)
    sp.set_defaults(func=cmd_orch_run)

    sp = osub.add_parser("sessions", help="list sessions")
    sp.add_argument("--root", default=None)
    sp.set_defaults(func=cmd_orch_sessions)

    sp = osub.add_parser("stop", help="stop a session")
    sp.add_argument("session_id")
    sp.add_argument("--root", default=None)
    sp.set_defaults(func=cmd_orch_stop)

    return p


def main(argv=None) -> int:
    _utf8()
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
