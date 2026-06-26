#!/usr/bin/env python3
"""
Undercover Mode — learning demo.

Walks through the three parts of Claude Code's (documented) Undercover Mode,
exactly as this plugin re-creates them:

  1. Activation logic   (isUndercover)
  2. System-prompt injection ("do not blow your cover")
  3. Enforcement        (detect / redact / block a cover-blowing commit)

Run:  python demo.py
Everything runs locally in a throwaway temp git repo — nothing is pushed.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

# import the undercover engine from ../scripts
SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
import undercover as uc  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore
except Exception:
    pass


def hr(title: str) -> None:
    print("\n" + "=" * 68)
    print(title)
    print("=" * 68)


def pause(label: str = "") -> None:
    # Non-interactive: just print a divider. (Kept simple for learning.)
    if label:
        print(f"\n--- {label} ---")


# ---------------------------------------------------------------------------
hr("PART 1 — ACTIVATION  (isUndercover)")
print("""\
The real rule:
  • CLAUDE_CODE_UNDERCOVER=1   -> forced ON (even in internal repos)
  • USER_TYPE must be 'ant'    -> otherwise the feature doesn't apply
  • else automatic            -> ON unless the git remote is internal
  • NO force-OFF              -> if unsure, stay undercover
""")

scenarios = [
    ("Forced on",                 {"CLAUDE_CODE_UNDERCOVER": "1"}),
    ("Non-ant user (off)",        {"CLAUDE_CODE_USER_TYPE": "external"}),
    ("ant user, no remote",       {"CLAUDE_CODE_USER_TYPE": "ant"}),
]
for name, env in scenarios:
    d = uc.is_undercover(cwd=tempfile.gettempdir(), env=env)
    flag = "🕶️  UNDERCOVER" if d.active else "🟢 normal"
    print(f"  {name:<24} -> {flag}   ({d.reason})")

# ---------------------------------------------------------------------------
hr("PART 2 — SYSTEM-PROMPT INJECTION")
print("When undercover is active, this block is injected so the MODEL itself")
print("knows not to blow its cover:\n")
print(uc.undercover_prompt())

# ---------------------------------------------------------------------------
hr("PART 3 — ENFORCEMENT  (detect / redact)")
dirty = (
    "Optimize tengu cache for opus-4-8\n"
    "\n"
    "See go/cc-perf and #claude-code-team.\n"
    "Co-Authored-By: Claude <noreply@anthropic.com>\n"
)
print("A 'cover-blowing' commit message:\n")
print("    " + dirty.replace("\n", "\n    "))

rules = uc.build_rules(uc.load_extra_terms())
findings = uc.scan(dirty, rules)
print(f"Scanner found {len(findings)} problem(s):")
for f in findings:
    print(f"  • [{f.category}] {f.match!r} — {f.reason}")

print("\nRedacted (what a clean message looks like):\n")
print("    " + uc.redact(dirty, rules).replace("\n", "\n    "))

# ---------------------------------------------------------------------------
hr("PART 4 — REAL GIT REPO: the commit-msg hook blocks a bad commit")
with tempfile.TemporaryDirectory() as tmp:
    def git(*args, **kw):
        return subprocess.run(["git", *args], cwd=tmp, capture_output=True, text=True, **kw)

    git("init", "-q")
    git("config", "user.email", "you@example.com")
    git("config", "user.name", "You")

    # install the undercover commit-msg hook (calls `undercover.py check-commit`)
    hook = Path(tmp) / ".git" / "hooks" / "commit-msg"
    hook.write_text(
        "#!/bin/sh\n"
        f'python "{SCRIPTS / "undercover.py"}" check-commit "$1" || exit 1\n',
        encoding="utf-8",
    )
    try:
        hook.chmod(0o755)
    except Exception:
        pass
    print(f"Installed commit-msg hook in throwaway repo: {tmp}")

    (Path(tmp) / "file.txt").write_text("hello\n", encoding="utf-8")
    git("add", ".")

    pause("Attempt 1: a cover-blowing commit message  (should be BLOCKED)")
    r = git("commit", "-m", "Add tengu cache, Co-Authored-By: Claude")
    print(f"git exit code: {r.returncode}  ({'BLOCKED ✅' if r.returncode else 'committed'})")
    print((r.stderr or r.stdout).strip()[:600])

    pause("Attempt 2: a clean, human-style message  (should SUCCEED)")
    r = git("commit", "-m", "Add cache layer to speed up lookups")
    print(f"git exit code: {r.returncode}  ({'committed ✅' if r.returncode == 0 else 'blocked'})")
    log = git("log", "--oneline")
    print("repo log now:")
    print("  " + (log.stdout.strip() or "(empty)"))

hr("DONE")
print("That is the full Undercover Mode loop: activation → prompt injection →")
print("detection/redaction → a real hook that blocks cover-blowing commits.")
