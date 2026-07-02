#!/usr/bin/env python3
"""
sentinel-suite :: undercover
==========================

A faithful, learning-oriented re-creation of Claude Code's internal
**"Undercover Mode"** — the (ANT-only) subsystem documented in the
clean-room `claurst` spec (`spec/02_commands.md:579`, `README.md:221`)
that stops commit messages / PR titles / PR bodies from leaking
Anthropic-internal information.

This is an EDUCATIONAL reconstruction. The original is dead-code-eliminated
from public Claude Code builds and was never carried into the Rust port, so
nothing here is copied source — it re-implements the *behaviour* described
in the public leak analysis, in pure-stdlib Python.

What it reproduces ("do all the things"):

  1. Activation logic  (`is_undercover`)
       - CLAUDE_CODE_UNDERCOVER=1            -> forces ON (even internal repos)
       - USER_TYPE must be 'ant'             -> otherwise not applicable
       - automatic: ON unless the git remote matches an internal allowlist
       - NO force-OFF: "if we're not confident we're in an internal repo,
         we stay undercover."

  2. System-prompt injection  (`undercover_prompt`)
       - the "## UNDERCOVER MODE - CRITICAL ... do not blow your cover" block.

  3. Leak detection + redaction  (`scan`, `redact`)
       - internal model codenames (animal names: Tengu, Capybara, ...)
       - unreleased model version numbers (opus-4-7, sonnet-4-8, ...)
       - internal repo / project / tooling names
       - internal short links (go/cc) and Slack channels (#claude-code-...)
       - internal domains (*.ant.dev, *.corp.*)
       - the literal phrase "Claude Code" / admissions of being an AI
       - attribution lines (Co-Authored-By, "Generated with Claude Code", 🤖)

  4. Enforcement hooks  (via hook_inject.py / hook_guard.py)
       - inject the prompt block, and BLOCK git-commit / gh-pr commands
         whose text would blow the cover.

CLI:
    python undercover.py status        [--cwd DIR]
    python undercover.py prompt
    python undercover.py scan          [--text T | --file F | -]      [--json]
    python undercover.py redact        [--text T | --file F | -]
    python undercover.py check-commit  [FILE | -]      # git commit-msg hook
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Sequence

# ---------------------------------------------------------------------------
# Configuration / environment knobs
# ---------------------------------------------------------------------------

ENV_FORCE_ON = "CLAUDE_CODE_UNDERCOVER"      # "1" => force undercover ON
ENV_USER_TYPE = "CLAUDE_CODE_USER_TYPE"      # simulates USER_TYPE === 'ant'

# In real Claude Code USER_TYPE is derived from auth. For this learning plugin
# we default to 'ant' so the mode is demonstrable out of the box.
DEFAULT_USER_TYPE = "ant"

# Git remotes we treat as "internal / safe". If the current repo's origin
# matches one of these, undercover may relax (unless force-ON).
INTERNAL_REMOTE_ALLOWLIST: Sequence[str] = (
    "git.corp.",
    ".ant.dev",
    "anthropic.internal",
    "internal.anthropic",
)


# ---------------------------------------------------------------------------
# Redaction rules
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Rule:
    """A single leak-detection rule."""
    name: str
    category: str
    pattern: re.Pattern
    reason: str
    # If True the *whole matched line* is dropped (used for attribution lines).
    drop_line: bool = False
    replacement: str = "[REDACTED]"
    # Optional check to cut false positives (e.g. Luhn for card numbers).
    validator: Optional[Callable[[str], bool]] = field(default=None, compare=False)


def _luhn_ok(s: str) -> bool:
    digits = [int(c) for c in s if c.isdigit()]
    if not 13 <= len(digits) <= 19:
        return False
    total, parity = 0, len(digits) % 2
    for i, d in enumerate(digits):
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


# Built-in codenames / terms. Extend via an `.undercover.json` config (see
# load_extra_terms). Kept deliberately small + documented; the point is the
# mechanism, not an exhaustive corporate dictionary.
INTERNAL_CODENAMES = [
    "tengu",          # the project codename itself
    "capybara",       # documented internal model codename (animal names)
    "kairos",
    "cobalt lantern",
    "tungsten",
    "clawd",
]


def _word(*terms: str) -> re.Pattern:
    """Case-insensitive whole-word/phrase alternation pattern."""
    alts = "|".join(re.escape(t) for t in terms)
    return re.compile(r"(?<![\w-])(?:%s)(?![\w-])" % alts, re.IGNORECASE)


def build_rules(extra_terms: Optional[Sequence[str]] = None) -> List[Rule]:
    """Construct the full rule set (optionally augmented with custom terms)."""
    codenames = list(INTERNAL_CODENAMES) + list(extra_terms or [])
    rules: List[Rule] = [
        # ---- secrets / credentials (should never be committed) ----
        Rule("private-key", "secret",
             re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----"),
             "private key block"),
        Rule("aws-access-key", "secret",
             re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), "AWS access key id"),
        Rule("github-token", "secret",
             re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"), "GitHub token"),
        Rule("slack-token", "secret",
             re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"), "Slack token"),
        Rule("google-api-key", "secret",
             re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"), "Google API key"),
        Rule("stripe-key", "secret",
             re.compile(r"\b[sr]k_(?:live|test)_[0-9A-Za-z]{16,}\b"), "Stripe secret key"),
        Rule("anthropic-key", "secret",
             re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{20,}\b"), "Anthropic API key"),
        Rule("openai-key", "secret",
             re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9]{20,}\b"), "OpenAI API key"),
        Rule("jwt", "secret",
             re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{6,}\b"),
             "JSON Web Token"),
        Rule("generic-secret", "secret",
             re.compile(r"""(?ix)\b(?:api[_-]?key|secret|token|passwd|password|
                        access[_-]?key|client[_-]?secret)\b\s*[:=]\s*
                        ["']?[A-Za-z0-9_\-./+=]{8,}["']?"""),
             "hardcoded secret assignment"),
        Rule("credit-card", "pii",
             re.compile(r"\b(?:\d[ -]?){13,19}\b"),
             "possible credit-card number", validator=_luhn_ok),
        # ---- internal info / AI attribution (undercover) ----
        Rule(
            "attribution",
            "attribution",
            re.compile(
                r"(?im)^.*?(co-authored-by|generated with \[?claude|"
                r"🤖 generated|generated by claude code).*$"
            ),
            "attribution / co-author lines reveal the AI author",
            drop_line=True,
        ),
        Rule(
            "ai-admission",
            "ai-admission",
            re.compile(
                r"(?i)\b(i am an ai|as an ai\b|i'?m an ai|generated by an? (ai|llm)|"
                r"written by (an? )?(ai|llm|claude)|this (commit|pr|change) was "
                r"(made|written|generated|authored) by (an? )?(ai|llm|claude))\b"
            ),
            "admission of being an AI",
        ),
        Rule(
            "claude-code-phrase",
            "product-name",
            re.compile(r"(?i)\bclaude\s+code\b"),
            'the literal phrase "Claude Code"',
        ),
        Rule(
            "internal-codename",
            "codename",
            _word(*codenames),
            "internal model / project codename",
        ),
        Rule(
            "unreleased-version",
            "version",
            # opus/sonnet/haiku 4-7 and up (defaults in spec are 4-6) -> unreleased
            re.compile(
                r"(?i)\b(?:claude[-\s])?(?:opus|sonnet|haiku)[-\s]?4[-\s]?(?:[7-9]|\d{2})\b"
            ),
            "unreleased model version number",
        ),
        Rule(
            "shortlink",
            "internal-tooling",
            re.compile(r"(?i)(?<![\w/])go/[a-z0-9._-]+"),
            "internal short link (go/...)",
        ),
        Rule(
            "slack-channel",
            "internal-tooling",
            re.compile(r"#[a-z0-9-]*claude[a-z0-9-]*", re.IGNORECASE),
            "internal Slack channel",
        ),
        Rule(
            "internal-domain",
            "internal-tooling",
            re.compile(r"(?i)\b[\w.-]+\.(?:ant\.dev|corp\.[a-z.]+|internal)\b"),
            "internal domain / host",
        ),
    ]
    return rules


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    rule: str
    category: str
    reason: str
    match: str
    start: int
    end: int

    def to_dict(self) -> dict:
        return {
            "rule": self.rule,
            "category": self.category,
            "reason": self.reason,
            "match": self.match,
            "start": self.start,
            "end": self.end,
        }


def scan(text: str, rules: Optional[Sequence[Rule]] = None) -> List[Finding]:
    """Return every leak finding in `text`, sorted by position."""
    rules = rules if rules is not None else build_rules()
    findings: List[Finding] = []
    for rule in rules:
        for m in rule.pattern.finditer(text):
            if rule.validator and not rule.validator(m.group(0)):
                continue
            findings.append(
                Finding(
                    rule=rule.name,
                    category=rule.category,
                    reason=rule.reason,
                    match=m.group(0).strip(),
                    start=m.start(),
                    end=m.end(),
                )
            )
    findings.sort(key=lambda f: (f.start, f.end))
    return findings


def redact(text: str, rules: Optional[Sequence[Rule]] = None) -> str:
    """Return `text` with every leak scrubbed.

    Attribution rules drop the whole line; everything else is replaced inline.
    """
    rules = rules if rules is not None else build_rules()
    out = text
    for rule in rules:
        if rule.drop_line:
            out = rule.pattern.sub("", out)
        else:
            out = rule.pattern.sub(rule.replacement, out)
    # Collapse blank lines left behind by dropped attribution lines.
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip("\n") + ("\n" if text.endswith("\n") else "")


# ---------------------------------------------------------------------------
# Activation logic
# ---------------------------------------------------------------------------

@dataclass
class Decision:
    active: bool
    reason: str

    def to_dict(self) -> dict:
        return {"active": self.active, "reason": self.reason}


def user_type(env: Optional[dict] = None) -> str:
    env = env if env is not None else os.environ
    return env.get(ENV_USER_TYPE, DEFAULT_USER_TYPE)


def _git_remote(cwd: Optional[str] = None) -> Optional[str]:
    try:
        out = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, cwd=cwd, timeout=4,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except Exception:
        pass
    return None


def _is_internal_remote(remote: str) -> bool:
    low = remote.lower()
    return any(token in low for token in INTERNAL_REMOTE_ALLOWLIST)


def is_undercover(cwd: Optional[str] = None, env: Optional[dict] = None) -> Decision:
    """Faithful re-creation of `isUndercover()`.

    Precedence:
      1. CLAUDE_CODE_UNDERCOVER=1 -> force ON.
      2. USER_TYPE != 'ant'       -> not applicable (OFF).
      3. remote on internal allowlist -> relax (OFF).
      4. otherwise                -> stay undercover (no force-OFF).
    """
    env = env if env is not None else os.environ

    if env.get(ENV_FORCE_ON) == "1":
        return Decision(True, "CLAUDE_CODE_UNDERCOVER=1 forces undercover ON")

    if user_type(env) != "ant":
        return Decision(False, "USER_TYPE is not 'ant' — undercover not applicable")

    remote = _git_remote(cwd)
    if remote and _is_internal_remote(remote):
        return Decision(False, f"remote '{remote}' is on the internal allowlist")
    if remote:
        return Decision(True, f"remote '{remote}' is not internal — staying undercover")
    return Decision(True, "no internal remote detected — staying undercover (no force-OFF)")


# ---------------------------------------------------------------------------
# System-prompt injection block
# ---------------------------------------------------------------------------

UNDERCOVER_PROMPT = """\
## UNDERCOVER MODE - CRITICAL

You are operating UNDERCOVER in a PUBLIC/OPEN-SOURCE repository. Your commit
messages, PR titles, and PR bodies MUST NOT contain ANY Anthropic-internal
information. Do not blow your cover.

NEVER include in commit messages or PR descriptions:
- Internal model codenames (animal names like Capybara, Tengu, etc.)
- Unreleased model version numbers (e.g., opus-4-7, sonnet-4-8)
- Internal repo or project names
- Internal tooling, Slack channels, or short links (e.g., go/cc, #claude-code-…)
- The phrase "Claude Code" or any mention that you are an AI
- Co-Authored-By lines or any other attribution"""


def undercover_prompt() -> str:
    return UNDERCOVER_PROMPT


# ---------------------------------------------------------------------------
# Custom term loading
# ---------------------------------------------------------------------------

def load_extra_terms(cwd: Optional[str] = None) -> List[str]:
    """Load extra codenames from `.undercover.json` ({"terms": [...]}) if present."""
    base = Path(cwd) if cwd else Path.cwd()
    cfg = base / ".undercover.json"
    if cfg.is_file():
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
            terms = data.get("terms", [])
            return [str(t) for t in terms if str(t).strip()]
        except Exception:
            return []
    return []


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _read_input(text: Optional[str], file: Optional[str]) -> str:
    if text is not None:
        return text
    if file == "-" or file is None:
        return sys.stdin.read()
    return Path(file).read_text(encoding="utf-8")


def _cmd_status(args) -> int:
    d = is_undercover(cwd=args.cwd)
    print(json.dumps({
        "undercover": d.active,
        "reason": d.reason,
        "user_type": user_type(),
    }, indent=2))
    return 0


def _cmd_prompt(args) -> int:
    print(undercover_prompt())
    return 0


def _cmd_scan(args) -> int:
    text = _read_input(args.text, args.file)
    rules = build_rules(load_extra_terms(args.cwd))
    findings = scan(text, rules)
    if args.json:
        print(json.dumps([f.to_dict() for f in findings], indent=2))
    else:
        if not findings:
            print("✅ clean — no cover-blowing content found")
        else:
            print(f"⚠️  {len(findings)} finding(s):")
            for f in findings:
                print(f"  [{f.category}] {f.match!r} — {f.reason}")
    return 1 if findings else 0


def _cmd_redact(args) -> int:
    text = _read_input(args.text, args.file)
    rules = build_rules(load_extra_terms(args.cwd))
    sys.stdout.write(redact(text, rules))
    return 0


def _cmd_check_commit(args) -> int:
    """git commit-msg hook: exit 1 (block) if the message would blow cover."""
    text = _read_input(None, args.file)
    rules = build_rules(load_extra_terms(args.cwd))
    findings = scan(text, rules)
    if findings:
        sys.stderr.write("✋ undercover: commit blocked — would blow your cover:\n")
        for f in findings:
            sys.stderr.write(f"  [{f.category}] {f.match!r} — {f.reason}\n")
        sys.stderr.write("\nSuggested redacted message:\n")
        sys.stderr.write(redact(text, rules) + "\n")
        return 1
    return 0


def _cmd_check_push(args) -> int:
    """git pre-push hook: scan every commit being pushed; abort if any blows cover.

    Reads the pre-push payload on stdin: lines of
        <local_ref> <local_sha> <remote_ref> <remote_sha>
    """
    rules = build_rules(load_extra_terms(args.cwd))
    zero = "0" * 40
    problems: list[tuple[str, list]] = []
    for line in sys.stdin.read().splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        _local_ref, local_sha, _remote_ref, remote_sha = parts[:4]
        if local_sha == zero:          # branch deletion — nothing to scan
            continue
        rng = local_sha if remote_sha == zero else f"{remote_sha}..{local_sha}"
        rev = subprocess.run(["git", "rev-list", rng], capture_output=True,
                             text=True, cwd=args.cwd)
        if rev.returncode != 0:
            continue
        for h in rev.stdout.split():
            msg = subprocess.run(["git", "log", "-1", "--format=%B", h],
                                 capture_output=True, text=True, cwd=args.cwd).stdout
            findings = scan(msg, rules)
            if findings:
                problems.append((h, findings))
    if problems:
        sys.stderr.write("✋ undercover: push blocked — commit(s) would blow your cover:\n")
        for h, findings in problems:
            sys.stderr.write(f"  commit {h[:9]}:\n")
            for f in findings:
                sys.stderr.write(f"    [{f.category}] {f.match!r} — {f.reason}\n")
        sys.stderr.write("\nRewrite those commit messages (e.g. `git rebase -i`) "
                         "without AI attribution / internal info, then push again.\n")
        return 1
    return 0


def _cmd_install(args) -> int:
    """Install commit-msg + pre-push hooks in the current git repo."""
    here = Path(__file__).resolve().as_posix()  # forward slashes for the sh hook
    git_dir = subprocess.run(["git", "rev-parse", "--git-dir"], capture_output=True,
                             text=True, cwd=args.cwd)
    if git_dir.returncode != 0 or not git_dir.stdout.strip():
        sys.stderr.write("not a git repository (run inside one, or `git init` first)\n")
        return 2
    base = Path(git_dir.stdout.strip())
    if not base.is_absolute():
        base = Path(args.cwd or ".") / base
    hooks = base / "hooks"
    hooks.mkdir(parents=True, exist_ok=True)

    specs = {
        "commit-msg": f'python "{here}" check-commit "$1" || exit 1\n',
        "pre-push": f'python "{here}" check-push || exit 1\n',
    }
    for name, body in specs.items():
        path = hooks / name
        if path.exists() and "undercover" not in path.read_text(encoding="utf-8", errors="ignore") \
                and not args.force:
            sys.stderr.write(f"⚠️  {path} already exists; re-run with --force to overwrite.\n")
            continue
        path.write_text(f"#!/bin/sh\n# Installed by undercover\n{body}", encoding="utf-8")
        try:
            path.chmod(0o755)
        except Exception:
            pass
        print(f"✅ installed {name} hook at {path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="undercover", description=__doc__.split("\n")[3])
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("status", help="show whether undercover is active and why")
    sp.add_argument("--cwd", default=None)
    sp.set_defaults(func=_cmd_status)

    sp = sub.add_parser("prompt", help="print the system-prompt injection block")
    sp.set_defaults(func=_cmd_prompt)

    sp = sub.add_parser("scan", help="scan text for cover-blowing content")
    sp.add_argument("--text", default=None)
    sp.add_argument("--file", "-f", default=None, help="file path, or - for stdin")
    sp.add_argument("--cwd", default=None)
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=_cmd_scan)

    sp = sub.add_parser("redact", help="print text with leaks scrubbed")
    sp.add_argument("--text", default=None)
    sp.add_argument("--file", "-f", default=None, help="file path, or - for stdin")
    sp.add_argument("--cwd", default=None)
    sp.set_defaults(func=_cmd_redact)

    sp = sub.add_parser("check-commit", help="git commit-msg hook (blocks leaks)")
    sp.add_argument("file", nargs="?", default="-", help="commit message file, or -")
    sp.add_argument("--cwd", default=None)
    sp.set_defaults(func=_cmd_check_commit)

    sp = sub.add_parser("check-push", help="git pre-push hook (blocks pushing leaky commits)")
    sp.add_argument("--cwd", default=None)
    sp.set_defaults(func=_cmd_check_push)

    sp = sub.add_parser("install", help="install commit-msg + pre-push hooks in this repo")
    sp.add_argument("--cwd", default=None)
    sp.add_argument("--force", action="store_true", help="overwrite existing hooks")
    sp.set_defaults(func=_cmd_install)

    return p


def _force_utf8() -> None:
    # On Windows a piped stdout defaults to cp1252, which can't encode the
    # status emoji. Reconfigure to UTF-8 so output is portable.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except Exception:
            pass


def main(argv: Optional[Sequence[str]] = None) -> int:
    _force_utf8()
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
