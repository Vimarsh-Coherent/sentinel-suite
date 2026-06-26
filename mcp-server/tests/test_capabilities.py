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


def test_info():
    i = cap.info()
    assert i["name"] == "sentinel-suite"
    assert "Sentinel Suite Guard" in i["capabilities"]


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
