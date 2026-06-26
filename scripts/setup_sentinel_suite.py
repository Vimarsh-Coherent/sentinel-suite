#!/usr/bin/env python3
"""
Sentinel Suite — one-shot setup for a new user/machine.

Anyone who clones Sentinel Suite can run this to opt in to attribution-free
commits and learn the next steps. It is safe and idempotent: it merges one key
into your existing global Claude Code settings without touching anything else.

What it does:
  • sets  "includeCoAuthoredBy": false  in ~/.claude/settings.json
    (the official Claude Code switch that stops the "Co-Authored-By: Claude"
     trailer + "Generated with Claude Code" line on commits/PRs)
  • prints the next steps to install the plugins / MCP server

Usage:
    python scripts/setup_sentinel_suite.py                  # opt in (settings only)
    python scripts/setup_sentinel_suite.py --global-hooks   # ALSO guard every repo on this machine
    python scripts/setup_sentinel_suite.py --path P         # apply to a specific settings file
    python scripts/setup_sentinel_suite.py --dry-run        # show what would change
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def default_settings_path() -> Path:
    return Path.home() / ".claude" / "settings.json"


def repo_root() -> Path:
    # scripts/setup_sentinel_suite.py -> sentinel-suite/
    return Path(__file__).resolve().parents[1]


def undercover_script() -> Path:
    return repo_root() / "plugins" / "undercover" / "scripts" / "undercover.py"


def install_global_hooks(hooks_dir: Path, dry_run: bool) -> None:
    """Write commit-msg + pre-push hooks and point git's global core.hooksPath at them.

    This protects EVERY repo on the machine (blocks committing/pushing AI
    attribution) without per-repo installation.
    """
    uc = undercover_script().as_posix()
    specs = {
        "commit-msg": f'#!/bin/sh\n# Sentinel Suite global hook\npython "{uc}" check-commit "$1" || exit 1\n',
        "pre-push": f'#!/bin/sh\n# Sentinel Suite global hook\npython "{uc}" check-push || exit 1\n',
    }
    print(f"\nGlobal hooks dir: {hooks_dir}")
    if dry_run:
        print(f"[dry-run] would write {', '.join(specs)} and run:")
        print(f"          git config --global core.hooksPath \"{hooks_dir.as_posix()}\"")
        return
    hooks_dir.mkdir(parents=True, exist_ok=True)
    for name, body in specs.items():
        p = hooks_dir / name
        p.write_text(body, encoding="utf-8")
        try:
            p.chmod(0o755)
        except Exception:
            pass
        print(f"✅ wrote {name}")
    subprocess.run(["git", "config", "--global", "core.hooksPath", hooks_dir.as_posix()],
                   check=False)
    print(f"✅ set git global core.hooksPath -> {hooks_dir.as_posix()}")
    print("   (note: a global hooksPath overrides any per-repo .git/hooks)")


def load(path: Path) -> dict:
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8") or "{}")
        except json.JSONDecodeError:
            print(f"⚠️  {path} is not valid JSON; refusing to overwrite. "
                  "Fix or remove it first.", file=sys.stderr)
            raise SystemExit(2)
    return {}


def _force_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except Exception:
            pass


def main(argv: list[str] | None = None) -> int:
    _force_utf8()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--path", default=None, help="settings file (default: ~/.claude/settings.json)")
    ap.add_argument("--global-hooks", action="store_true",
                    help="also guard EVERY repo on this machine via git core.hooksPath")
    ap.add_argument("--hooks-dir", default=None,
                    help="where to write global hooks (default: ~/.sentinel-suite/hooks)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    path = Path(args.path) if args.path else default_settings_path()
    settings = load(path)

    already = settings.get("includeCoAuthoredBy") is False
    if already:
        print(f"✅ Already set: includeCoAuthoredBy=false in {path}")
    else:
        settings["includeCoAuthoredBy"] = False
        if args.dry_run:
            print(f"[dry-run] would set includeCoAuthoredBy=false in {path}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
            print(f"✅ Set includeCoAuthoredBy=false in {path}")

    if args.global_hooks:
        hooks_dir = Path(args.hooks_dir) if args.hooks_dir else (Path.home() / ".sentinel-suite" / "hooks")
        install_global_hooks(hooks_dir, args.dry_run)

    print("\nNext steps (optional):")
    print("  1. Install the plugins:")
    print("       /plugin marketplace add <path-to>/sentinel-suite")
    print("       /plugin install sentinel-guard@sentinel-suite")
    print("  2. Or connect the unified MCP server:")
    print("       cd sentinel-suite/mcp-server && pip install -e .")
    print("     then add it to your client's MCP config (see mcp-server/README.md).")
    print("\nNote: this controls attribution on YOUR commits. Don't use it to")
    print("deceive anyone who requires AI-use disclosure.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
