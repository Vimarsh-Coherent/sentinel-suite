"""Tests for the undercover core module. Run: python -m pytest, or python tests/test_undercover.py"""

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import undercover as uc  # noqa: E402


# ---- scan ----------------------------------------------------------------

def test_scan_detects_codename():
    f = uc.scan("optimize tengu cache path")
    assert any(x.category == "codename" for x in f)


def test_scan_detects_unreleased_version():
    f = uc.scan("bump default to opus-4-7")
    assert any(x.category == "version" for x in f)
    # released version should NOT trip the version rule
    f2 = uc.scan("bump default to sonnet-4-6")
    assert not any(x.category == "version" for x in f2)


def test_scan_detects_attribution_and_phrase():
    text = "Fix bug\n\nGenerated with Claude Code\nCo-Authored-By: Claude <noreply@anthropic.com>"
    cats = {x.category for x in uc.scan(text)}
    assert "attribution" in cats
    assert "product-name" in cats


def test_scan_detects_tooling():
    cats = {x.category for x in uc.scan("see go/cc and #claude-code-team and api.ant.dev")}
    assert "internal-tooling" in cats


def test_clean_text_has_no_findings():
    assert uc.scan("Fix race condition in cache eviction under load") == []


# ---- redact --------------------------------------------------------------

def test_redact_removes_attribution_line():
    text = "Fix bug\n\nCo-Authored-By: Claude <x@y.z>\n"
    out = uc.redact(text)
    assert "Co-Authored-By" not in out
    assert "Fix bug" in out


def test_redact_scrubs_codename_and_version():
    out = uc.redact("speed up tengu on opus-4-8")
    assert "tengu" not in out.lower()
    assert "opus-4-8" not in out.lower()
    assert "[REDACTED]" in out


# ---- activation ----------------------------------------------------------

def test_force_on():
    d = uc.is_undercover(env={uc.ENV_FORCE_ON: "1"})
    assert d.active


def test_non_ant_not_applicable():
    d = uc.is_undercover(env={uc.ENV_USER_TYPE: "external"})
    assert not d.active


def test_ant_default_stays_undercover_without_remote(tmp_path=None):
    # An empty dir has no git remote -> stay undercover (no force-OFF).
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        dec = uc.is_undercover(cwd=d, env={uc.ENV_USER_TYPE: "ant"})
        assert dec.active


# ---- custom terms --------------------------------------------------------

def test_extra_terms_loaded(tmp_path=None):
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / ".undercover.json").write_text(json.dumps({"terms": ["bluefin"]}))
        terms = uc.load_extra_terms(d)
        assert "bluefin" in terms
        rules = uc.build_rules(terms)
        assert any(x.category == "codename" for x in uc.scan("ship bluefin now", rules))


# ---- CLI -----------------------------------------------------------------

def test_cli_scan_exit_code():
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "undercover.py"), "scan", "--text", "use tengu"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert r.returncode == 1  # findings -> non-zero

    r2 = subprocess.run(
        [sys.executable, str(SCRIPTS / "undercover.py"), "scan", "--text", "fix the loop"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert r2.returncode == 0


def test_detects_secrets():
    rules = uc.build_rules()
    cats = {f.category for f in uc.scan("deploy AKIAABCDEFGHIJKLMNOP and password=hunter2secret", rules)}
    assert "secret" in cats


def test_credit_card_luhn():
    rules = uc.build_rules()
    assert any(f.category == "pii" for f in uc.scan("card 4111 1111 1111 1111", rules))
    assert not any(f.category == "pii" for f in uc.scan("id 1234 5678 9012 3456", rules))


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        passed += 1
        print(f"  ok  {fn.__name__}")
    print(f"\n{passed}/{len(fns)} tests passed")


if __name__ == "__main__":
    _run_all()
