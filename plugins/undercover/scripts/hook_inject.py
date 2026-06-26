#!/usr/bin/env python3
"""
UserPromptSubmit / SessionStart hook.

When undercover mode is active, injects the "UNDERCOVER MODE - CRITICAL"
block into the model's context as additionalContext. This is how the real
subsystem gets the instructions in front of the model.

Reads the Claude Code hook payload as JSON on stdin and writes a JSON
response on stdout per the hook protocol.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Make the sibling library importable regardless of cwd.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import undercover  # noqa: E402


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}

    cwd = payload.get("cwd") or os.getcwd()
    decision = undercover.is_undercover(cwd=cwd)

    if not decision.active:
        # Emit nothing extra; let the turn proceed normally.
        print(json.dumps({}))
        return 0

    event = payload.get("hook_event_name", "UserPromptSubmit")
    context = (
        undercover.undercover_prompt()
        + f"\n\n(undercover active: {decision.reason})"
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": event,
            "additionalContext": context,
        }
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
