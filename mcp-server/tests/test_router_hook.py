"""Regression tests for the auto-router hook (score-scale bug)."""

import io
import json
from contextlib import redirect_stdout

from sentinel_suite_mcp import router_hook


def _run(prompt: str) -> dict:
    import sys
    stdin = sys.stdin
    sys.stdin = io.StringIO(json.dumps({"prompt": prompt}))
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            router_hook.main()
    finally:
        sys.stdin = stdin
    return json.loads(buf.getvalue() or "{}")


def test_hook_fires_on_strong_prompt():
    out = _run("review my code for security vulnerabilities")
    ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
    assert "Sentinel Suite auto-router" in ctx, "hook must suggest for a clearly relevant prompt"


def test_hook_quiet_on_noise():
    out = _run("hi there")
    assert out == {}, "hook must stay silent when nothing matches well"


def test_min_score_is_cosine_scale():
    # Guard against re-introducing the integer-scale threshold bug: cosine
    # scores are 0..1, so the cutoff must be well below 1.
    assert 0 < router_hook.MIN_SCORE < 1
