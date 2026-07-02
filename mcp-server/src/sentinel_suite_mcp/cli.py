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
import time
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


def _install_graph_hooks(project_dir: Optional[str] = None) -> str:
    """Merge code-review-graph auto-hooks into the project's .claude/settings.json.

    SessionStart -> build/status the graph; after every Edit/Write -> update it.
    So the graph stays current automatically — you never have to mention it.
    """
    settings = Path(project_dir or os.getcwd()) / ".claude" / "settings.json"
    data: dict = {}
    if settings.is_file():
        try:
            data = json.loads(settings.read_text(encoding="utf-8") or "{}")
        except json.JSONDecodeError:
            return f"skipped — {settings} is not valid JSON"
    hooks = data.setdefault("hooks", {})

    def _has(event: str, cmd_sub: str) -> bool:
        for grp in hooks.get(event, []):
            for h in grp.get("hooks", []):
                if cmd_sub in h.get("command", ""):
                    return True
        return False

    if not _has("SessionStart", "code-review-graph"):
        hooks.setdefault("SessionStart", []).append(
            {"hooks": [{"type": "command", "command": "code-review-graph status", "timeout": 15}]})
    if not _has("PostToolUse", "code-review-graph"):
        hooks.setdefault("PostToolUse", []).append(
            {"matcher": "Edit|Write",
             "hooks": [{"type": "command", "command": "code-review-graph update --skip-flows",
                        "timeout": 30}]})
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return f"auto-graph hooks written to {settings}"


def _install_router_hook(project_dir: Optional[str] = None) -> str:
    """Merge the auto-router UserPromptSubmit hook into .claude/settings.json."""
    settings = Path(project_dir or os.getcwd()) / ".claude" / "settings.json"
    data: dict = {}
    if settings.is_file():
        try:
            data = json.loads(settings.read_text(encoding="utf-8") or "{}")
        except json.JSONDecodeError:
            return f"skipped — {settings} is not valid JSON"
    hooks = data.setdefault("hooks", {})
    for grp in hooks.get("UserPromptSubmit", []):
        for h in grp.get("hooks", []):
            if "router_hook" in h.get("command", ""):
                return "auto-router already enabled"
    hooks.setdefault("UserPromptSubmit", []).append(
        {"hooks": [{"type": "command",
                    "command": "python -m sentinel_suite_mcp.router_hook", "timeout": 15}]})
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return f"auto-router hook written to {settings}"


def cmd_setup(a) -> int:
    """One command to wire ALL of Sentinel Suite into the current project."""
    print("== Sentinel Suite: setting up this project ==\n")

    # 1. Guardrail opt-in (no AI attribution on commits/PRs)
    print("[1/4] Guard — attribution-free commits")
    init_ns = argparse.Namespace(global_hooks=a.global_hooks)
    cmd_init(init_ns)

    # 2. Install the 67 agents + 271 skills into ./.claude
    print("\n[2/4] Skills — installing agents + skills into .claude/")
    _install_dir("agents", None)
    _install_dir("skills", None)

    # 3. Build the code graph AND install auto-hooks so it stays active
    print("\n[3/4] Graph — building + auto-activating the code knowledge graph")
    try:
        r = subprocess.run(["code-review-graph", "build"], timeout=600)
        print("   graph built" if r.returncode == 0 else "   (build returned non-zero)")
    except FileNotFoundError:
        print("   (build skipped — install with `pip install code-review-graph`)")
    except Exception as e:
        print(f"   (build skipped — {e})")
    print("   " + _install_graph_hooks())
    print("   → the graph now rebuilds on session start and updates after every edit,")
    print("     so Claude always has fresh code intelligence without you asking.")

    # 4. Auto-router (announces the best agent/skill for each prompt)
    if not a.no_auto_router:
        print("\n[4/4] Auto-router — suggest the best agent/skill on every prompt")
        print("   " + _install_router_hook())
        print("   → on each prompt, Claude will say which agent/skill it's using")
        print("     (you can say 'no' to skip). Disable with: setup --no-auto-router")

    # 4. Next steps
    print("\n[4/4] Done. Optional next steps:")
    print("   • Connect the MCP server — add to your .mcp.json:")
    print('       { "mcpServers": { "sentinel-suite": { "command": "sentinel-suite-mcp", "type": "stdio" } } }')
    print("   • Multi-session dashboard:  sentinel-suite orchestrate serve")
    print("   • Restart Claude Code to load the agents/skills.")
    print("\n✅ Sentinel Suite is set up. All parts are active in this project.")
    return 0


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


def cmd_orch_send(a) -> int:
    from .orchestrator import Orchestrator
    m = Orchestrator(a.root).send_message(a.sender, a.recipient, " ".join(a.message), a.subject or "")
    print(f"✅ message {m.id} sent: {m.sender} → {m.recipient}")
    return 0


def cmd_orch_inbox(a) -> int:
    from .orchestrator import Orchestrator
    msgs = Orchestrator(a.root).inbox(a.recipient, a.unread)
    if not msgs:
        print(f"no messages for '{a.recipient}'")
    for m in msgs:
        mark = "  " if m.read else "* "
        subj = f"({m.subject}) " if m.subject else ""
        print(f"{mark}[{m.id}] {m.sender} → {m.recipient}: {subj}{m.body}")
    return 0


def cmd_orch_messages(a) -> int:
    from .orchestrator import Orchestrator
    msgs = Orchestrator(a.root)._all_messages()
    if not msgs:
        print("no messages yet")
    for m in msgs:
        print(f"  [{m.id}] {m.sender} → {m.recipient}: {m.body}")
    return 0


def cmd_orch_team(a) -> int:
    """Spin up a coordinator + N workers, each already in auto-inbox mode."""
    from .orchestrator import Orchestrator
    o = Orchestrator(a.root)
    handler = a.handler or 'claude -p "{body}"'
    coord = a.coordinator

    o.create_tentacle(coord, scope="assigns work + collects results")
    print(f"👥 team in {o.root}\n  coordinator: {coord}")
    for w in a.workers:
        o.create_tentacle(w)
        watch_cmd = (
            f'"{sys.executable}" -m sentinel_suite_mcp.cli orchestrate watch {w} '
            f'--on-message "{handler}" --root "{o.root}"'
        )
        if a.dry_run:
            print(f"  worker {w}: [dry-run] would run -> {watch_cmd}")
        else:
            s = o.spawn_session(w, watch_cmd)
            print(f"  worker {w}: watching (session {s.id}, pid {s.pid})")

    print("\nTalk to the team:")
    print(f"  sentinel-suite orchestrate send {coord} {a.workers[0] if a.workers else '<worker>'} \"do X\" --root \"{o.root}\"")
    print(f"  sentinel-suite orchestrate messages --root \"{o.root}\"")
    print("Tear down:  sentinel-suite orchestrate stop-all --root \"" + str(o.root) + "\"")
    return 0


def cmd_orch_stop_all(a) -> int:
    from .orchestrator import Orchestrator
    o = Orchestrator(a.root)
    stopped = 0
    for s in o.list_sessions():
        if s.status == "running":
            r = o.stop_session(s.id)
            if r.get("ok"):
                stopped += 1
                print(f"  stopped {s.id}")
    print(f"✅ stopped {stopped} running session(s)")
    return 0


def cmd_orch_watch(a) -> int:
    """Auto-inbox: poll a tentacle's inbox; print (and optionally run a handler)."""
    from .orchestrator import Orchestrator
    o = Orchestrator(a.root)
    print(f"👀 watching inbox for '{a.tentacle}' every {a.interval}s (Ctrl+C to stop)")
    try:
        while True:
            for m in o.inbox(a.tentacle, unread_only=True):
                print(f"[{m.id}] {m.sender} → {m.recipient}: {m.body}")
                if a.on_message:
                    cmd = (a.on_message.replace("{body}", m.body)
                           .replace("{sender}", m.sender).replace("{id}", m.id))
                    subprocess.run(cmd, shell=True)
                o.mark_read(m.id)
            if a.once:
                break
            time.sleep(a.interval)
    except KeyboardInterrupt:
        print("\nstopped.")
    return 0


# ---- router + skill authoring ----------------------------------------------

def cmd_recommend(a) -> int:
    rec = cap.recommend(" ".join(a.prompt), a.kind, a.top,
                        method="embed" if a.embed else "tfidf")
    if a.json:
        print(json.dumps(rec, indent=2))
        return 0
    if rec["agents"]:
        print("Best agents:")
        for it in rec["agents"]:
            print(f"  • {it['name']:<26} (score {it['score']})  {it['description'][:60]}")
    if rec["skills"]:
        print("Best skills:")
        for it in rec["skills"]:
            print(f"  • {it['name']:<26} (score {it['score']})  {it['description'][:60]}")
    if not rec["agents"] and not rec["skills"]:
        print("No strong match. Try `sentinel-suite agents` / `skills` to browse.")
    return 0


def cmd_skill_new(a) -> int:
    r = cap.create_skill(a.name, a.description or "", a.body or "")
    print(f"✅ created skill '{r['name']}' at {r['created']}")
    print("   Restart Claude Code to load it.")
    return 0


def cmd_connect(a) -> int:
    from . import adapters
    res = adapters.connect(a.target, root=a.root)
    for tool, files in res.items():
        print(f"✅ {tool}:")
        for f in files:
            print(f"   - {f}")
    print("\nRestart the tool so it picks up the MCP server + rules.")
    return 0


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

    sp = sub.add_parser("setup", help="ONE command: wire ALL of Sentinel Suite into this project")
    sp.add_argument("--global-hooks", action="store_true",
                    help="also guard every repo on this machine")
    sp.add_argument("--no-auto-router", action="store_true",
                    help="don't install the per-prompt agent/skill auto-router hook")
    sp.set_defaults(func=cmd_setup)

    sp = sub.add_parser("recommend", help="given a prompt, suggest the best agent(s)/skill(s)")
    sp.add_argument("prompt", nargs="+")
    sp.add_argument("--kind", choices=["both", "agents", "skills"], default="both")
    sp.add_argument("--top", type=int, default=5)
    sp.add_argument("--embed", action="store_true",
                    help="use true embeddings (needs the 'embeddings' extra)")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_recommend)

    sp = sub.add_parser("skill-new", help="create a new skill (./.claude/skills/<name>/SKILL.md)")
    sp.add_argument("name")
    sp.add_argument("--description", default=None)
    sp.add_argument("--body", default=None)
    sp.set_defaults(func=cmd_skill_new)

    sp = sub.add_parser("connect", help="wire Sentinel Suite into another tool (Cursor/Windsurf/Zed/Claude)")
    sp.add_argument("--target", required=True,
                    choices=["claude", "cursor", "windsurf", "zed", "all"])
    sp.add_argument("--root", default=None, help="SENTINEL_SUITE_ROOT for full checkout features")
    sp.set_defaults(func=cmd_connect)

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

    sp = osub.add_parser("send", help="send a message to a tentacle (or 'all')")
    sp.add_argument("sender")
    sp.add_argument("recipient")
    sp.add_argument("message", nargs="+")
    sp.add_argument("--subject", default=None)
    sp.add_argument("--root", default=None)
    sp.set_defaults(func=cmd_orch_send)

    sp = osub.add_parser("inbox", help="read messages for a tentacle")
    sp.add_argument("recipient")
    sp.add_argument("--unread", action="store_true")
    sp.add_argument("--root", default=None)
    sp.set_defaults(func=cmd_orch_inbox)

    sp = osub.add_parser("messages", help="show all messages")
    sp.add_argument("--root", default=None)
    sp.set_defaults(func=cmd_orch_messages)

    sp = osub.add_parser("team", help="spin up a coordinator + N workers in auto-inbox mode")
    sp.add_argument("workers", nargs="+", help="worker tentacle names (e.g. frontend backend docs)")
    sp.add_argument("--coordinator", default="coordinator")
    sp.add_argument("--handler", default=None,
                    help='per-message command (default: claude -p "{body}")')
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--root", default=None)
    sp.set_defaults(func=cmd_orch_team)

    sp = osub.add_parser("stop-all", help="stop all running sessions")
    sp.add_argument("--root", default=None)
    sp.set_defaults(func=cmd_orch_stop_all)

    sp = osub.add_parser("watch", help="auto-inbox: poll a tentacle's inbox and act on messages")
    sp.add_argument("tentacle")
    sp.add_argument("--interval", type=float, default=5.0)
    sp.add_argument("--on-message", default=None,
                    help="shell command to run per message ({body},{sender},{id} substituted)")
    sp.add_argument("--once", action="store_true", help="check once and exit (for testing)")
    sp.add_argument("--root", default=None)
    sp.set_defaults(func=cmd_orch_watch)

    return p


def main(argv=None) -> int:
    _utf8()
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
