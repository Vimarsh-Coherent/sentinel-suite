#!/usr/bin/env python3
"""
PreToolUse hook (matcher: Bash / PowerShell).

The enforcement half of undercover mode. Before a shell command runs, if the
command is a git-commit / git-tag / gh-pr style operation AND undercover is
active, scan the command text for cover-blowing content. If anything is found,
DENY the tool call with an explanation and a redacted suggestion — so the model
rewrites the message instead of leaking.

Hook protocol: JSON payload on stdin; JSON decision on stdout.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import undercover  # noqa: E402

# Commands whose text becomes public (commit messages, tags, PR titles/bodies).
PUBLISHING_CMD = re.compile(
    r"(?i)\b(git\s+commit|git\s+tag\b|git\s+merge\b|"
    r"gh\s+pr\s+(create|edit)|gh\s+release\s+create|gh\s+issue\s+(create|comment))\b"
)


def _command_text(payload: dict) -> str:
    ti = payload.get("tool_input") or {}
    # Bash uses "command"; PowerShell tool also uses "command".
    return ti.get("command") or ti.get("script") or ""


def _allow() -> int:
    print(json.dumps({}))
    return 0


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return _allow()

    command = _command_text(payload)
    if not command or not PUBLISHING_CMD.search(command):
        return _allow()

    cwd = payload.get("cwd") or os.getcwd()
    if not undercover.is_undercover(cwd=cwd).active:
        return _allow()

    rules = undercover.build_rules(undercover.load_extra_terms(cwd))
    findings = undercover.scan(command, rules)
    if not findings:
        return _allow()

    bullets = "\n".join(
        f"  - [{f.category}] {f.match!r}: {f.reason}" for f in findings
    )
    reason = (
        "Undercover mode: this command would publish cover-blowing content.\n"
        f"{bullets}\n\n"
        "Rewrite the commit/PR text as an ordinary human contributor would "
        "(no internal codenames, versions, tooling, AI attribution, or the "
        'phrase "Claude Code"), then try again.'
    )

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
