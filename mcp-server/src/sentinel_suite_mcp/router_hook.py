"""UserPromptSubmit hook — the auto-router.

On every prompt you type, this quietly finds the best-matching ecc agent/skill
and injects a note telling the model to **announce** what it's about to use and
proceed (so you always see it and can redirect). It does NOT silently force a
choice, and it stays quiet when nothing matches well.

Wired by `sentinel-suite setup` into .claude/settings.json:
    UserPromptSubmit -> python -m sentinel_suite_mcp.router_hook
"""

from __future__ import annotations

import json
import sys

# Only suggest when the match is clearly relevant (avoid noise on every prompt).
MIN_SCORE = 4


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}

    prompt = (payload.get("prompt") or payload.get("user_prompt") or "").strip()
    if not prompt:
        print(json.dumps({}))
        return 0

    try:
        from . import capabilities as cap
        rec = cap.recommend(prompt, top=1)
    except Exception:
        print(json.dumps({}))
        return 0

    agent = rec["agents"][0] if rec["agents"] else None
    skill = rec["skills"][0] if rec["skills"] else None
    picks = []
    if agent and agent["score"] >= MIN_SCORE:
        picks.append(f"the **{agent['name']}** agent")
    if skill and skill["score"] >= MIN_SCORE:
        picks.append(f"the **{skill['name']}** skill")

    if not picks:
        print(json.dumps({}))  # nothing strong — stay quiet
        return 0

    joined = " and ".join(picks)
    context = (
        f"[Sentinel Suite auto-router] For this request, the best match is {joined}. "
        f"Before doing the work, tell the user in ONE short line: "
        f"\"🧭 Sentinel Suite suggests {joined} for this — using it (say 'no' to skip).\" "
        f"Then proceed using it. If the user objects, drop it and continue normally."
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        }
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
