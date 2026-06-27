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

    sp = sub.add_parser("init", help="opt in: no AI attribution on commits/PRs")
    sp.add_argument("--global-hooks", action="store_true",
                    help="also guard every repo on this machine")
    sp.set_defaults(func=cmd_init)

    return p


def main(argv=None) -> int:
    _utf8()
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
