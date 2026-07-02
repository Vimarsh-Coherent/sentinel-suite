import json

from sentinel_suite_mcp import adapters


def test_connect_cursor(tmp_path):
    adapters.connect("cursor", cwd=str(tmp_path))
    mcp = tmp_path / ".cursor" / "mcp.json"
    rule = tmp_path / ".cursor" / "rules" / "sentinel-suite.mdc"
    assert mcp.is_file() and rule.is_file()
    assert "sentinel-suite" in json.loads(mcp.read_text())["mcpServers"]
    assert "alwaysApply: true" in rule.read_text()


def test_connect_all(tmp_path):
    res = adapters.connect("all", cwd=str(tmp_path))
    assert set(res) == {"claude", "cursor", "windsurf", "zed"}
    assert (tmp_path / ".mcp.json").is_file()                       # claude
    assert (tmp_path / ".cursor" / "mcp.json").is_file()           # cursor
    assert (tmp_path / ".windsurf" / "rules" / "sentinel-suite.md").is_file()
    assert (tmp_path / ".zed" / "sentinel-suite.mcp.json").is_file()


def test_mcp_merge_preserves_existing(tmp_path):
    p = tmp_path / ".cursor" / "mcp.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({"mcpServers": {"other": {"command": "x"}}}))
    adapters.connect("cursor", cwd=str(tmp_path))
    servers = json.loads(p.read_text())["mcpServers"]
    assert "other" in servers and "sentinel-suite" in servers  # kept both
