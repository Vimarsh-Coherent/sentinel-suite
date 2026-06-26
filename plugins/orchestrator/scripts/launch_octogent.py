#!/usr/bin/env python3
"""
Launch the vendored Octogent dashboard.

Octogent (https://github.com/hesamsheikh/octogent, MIT) is a Node.js app that
orchestrates multiple Claude Code sessions. It is NOT a Claude Code plugin or an
MCP server, so it can't live in the marketplace — instead we vendor it and this
helper boots it from source.

Requirements: Node >= 22 and pnpm (this script will try `corepack enable pnpm`
if pnpm is missing). First run does `pnpm install`; subsequent runs skip it
unless --install is passed.

Usage:
    python launch_octogent.py [--install] [--build]
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# plugins/orchestrator/scripts/ -> repo root is parents[3]
REPO_ROOT = Path(__file__).resolve().parents[3]
OCTOGENT = REPO_ROOT / "vendor" / "octogent"


def _run(cmd: list[str], cwd: Path) -> int:
    print(f"$ {' '.join(cmd)}  (in {cwd})")
    return subprocess.call(cmd, cwd=str(cwd), shell=(sys.platform == "win32"))


def _have(exe: str) -> bool:
    return shutil.which(exe) is not None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--install", action="store_true", help="force `pnpm install`")
    ap.add_argument("--build", action="store_true", help="run `pnpm build` instead of dev")
    args = ap.parse_args()

    if not OCTOGENT.is_dir():
        print(f"ERROR: vendored octogent not found at {OCTOGENT}", file=sys.stderr)
        print("Clone it: git clone --depth 1 https://github.com/hesamsheikh/octogent "
              f"{OCTOGENT}", file=sys.stderr)
        return 2

    if not _have("node"):
        print("ERROR: Node.js >= 22 is required (https://nodejs.org/).", file=sys.stderr)
        return 2

    if not _have("pnpm"):
        print("pnpm not found — trying `corepack enable pnpm` ...")
        if _have("corepack"):
            _run(["corepack", "enable", "pnpm"], REPO_ROOT)
        if not _have("pnpm"):
            print("ERROR: pnpm still unavailable. Install via: npm i -g pnpm",
                  file=sys.stderr)
            return 2

    if args.install or not (OCTOGENT / "node_modules").is_dir():
        rc = _run(["pnpm", "install"], OCTOGENT)
        if rc != 0:
            return rc

    target = ["pnpm", "build"] if args.build else ["pnpm", "dev"]
    print(f"Starting Octogent ({'build' if args.build else 'dev'}) — UI usually at "
          "http://localhost:8787")
    return _run(target, OCTOGENT)


if __name__ == "__main__":
    raise SystemExit(main())
