import asyncio

from sentinel_suite_mcp import capabilities as cap
from sentinel_suite_mcp.server import mcp


def test_guardrail_scan_and_redact():
    findings = cap.guardrail_scan("ship tengu (Co-Authored-By: AI)")
    assert findings and any(f["category"] == "codename" for f in findings)
    clean = cap.guardrail_redact("ship tengu now")
    assert "tengu" not in clean.lower()


def test_guardrail_status():
    s = cap.guardrail_status()
    assert "active" in s and "reason" in s


def test_ecc_skills_listed_and_fetchable():
    skills = cap.ecc_list_skills()
    assert len(skills) > 50, "expected the vendored ecc skills to be present"
    one = skills[0]["name"]
    assert "name" in skills[0] and "description" in skills[0]
    content = cap.ecc_get_skill(one)
    assert content and "skill not found" not in content


def test_ecc_skills_query_filters():
    all_skills = cap.ecc_list_skills()
    filtered = cap.ecc_list_skills("security")
    assert len(filtered) <= len(all_skills)


def test_ecc_agents_listed():
    agents = cap.ecc_list_agents()
    assert len(agents) > 20


def test_create_tentacle(tmp_path):
    msg = cap.create_tentacle("docs-pass", "documentation work", cwd=str(tmp_path))
    base = tmp_path / ".octogent" / "tentacles" / "docs-pass"
    assert (base / "CONTEXT.md").is_file()
    assert (base / "todo.md").is_file()
    assert "created tentacle" in msg


def test_recommend_surfaces_matches():
    rec = cap.recommend("add unit tests with test driven development")
    assert rec["agents"] or rec["skills"]
    for group in ("agents", "skills"):
        scores = [x["score"] for x in rec[group]]
        assert scores == sorted(scores, reverse=True)


def test_recommend_empty_prompt():
    rec = cap.recommend("")
    assert rec["agents"] == [] and rec["skills"] == []


def test_create_skill(tmp_path):
    r = cap.create_skill("My Cool Skill", "does cool things", cwd=str(tmp_path))
    p = tmp_path / ".claude" / "skills" / "my-cool-skill" / "SKILL.md"
    assert p.is_file()
    text = p.read_text(encoding="utf-8")
    assert "name: my-cool-skill" in text
    assert "does cool things" in text


def test_info():
    i = cap.info()
    assert i["name"] == "sentinel-suite"
    assert "Sentinel Suite Guard" in i["capabilities"]


def test_repo_root_ignores_stale_env(tmp_path, monkeypatch):
    # A SENTINEL_SUITE_ROOT that isn't a real checkout (no vendor/ or plugins/)
    # must be ignored, not trusted — otherwise it silently masks the bundle.
    stale = tmp_path / "not-a-checkout"
    stale.mkdir()
    monkeypatch.setenv("SENTINEL_SUITE_ROOT", str(stale))
    root = cap.repo_root()
    assert root != stale, "stale root without vendor/ or plugins/ must be rejected"


def test_ecc_available_despite_mispointed_root(tmp_path, monkeypatch):
    # Even when the env var points at a checkout-shaped dir that lacks vendor/ecc,
    # the ecc skills/agents must still resolve (via the in-tree / bundled fallback).
    fake_checkout = tmp_path / "other-checkout"
    (fake_checkout / "plugins").mkdir(parents=True)  # looks like a checkout, no vendor/ecc
    monkeypatch.setenv("SENTINEL_SUITE_ROOT", str(fake_checkout))
    skills = cap.ecc_list_skills()
    assert len(skills) > 50, "ecc data must resolve independently of a mispointed root"
    assert skills[0]["name"] != "(unavailable)"


def test_server_exposes_all_tools():
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    for expected in [
        "guardrail_scan", "guardrail_redact", "guardrail_status",
        "ecc_list_skills", "ecc_get_skill", "ecc_list_agents", "ecc_get_agent",
        "code_graph", "create_tentacle", "octogent_launch_command",
        "sentinel_suite_info",
    ]:
        assert expected in names, f"missing tool: {expected}"
