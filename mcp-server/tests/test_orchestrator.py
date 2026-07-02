import json
import sys
import threading
import time
import urllib.request

from sentinel_suite_mcp.orchestrator import Orchestrator
from sentinel_suite_mcp.orchestrator_server import make_handler
from http.server import ThreadingHTTPServer


def test_scaffold_and_tentacle(tmp_path):
    o = Orchestrator(str(tmp_path))
    o.scaffold()
    assert (tmp_path / ".octogent" / "tentacles").is_dir()
    t = o.create_tentacle("Docs Pass", scope="documentation")
    assert t.id == "docs-pass"
    base = tmp_path / ".octogent" / "tentacles" / "docs-pass"
    assert (base / "CONTEXT.md").is_file()
    assert (base / "todo.md").is_file()
    assert (base / "meta.json").is_file()
    ids = [x.id for x in o.list_tentacles()]
    assert "docs-pass" in ids


def test_session_lifecycle(tmp_path):
    o = Orchestrator(str(tmp_path))
    # a quick command that exits fast
    s = o.spawn_session("work", f'"{sys.executable}" -c "print(1)"')
    assert s.pid
    sessions = o.list_sessions()
    assert any(x.id == s.id for x in sessions)
    # after it finishes, status should read finished (give it a moment)
    for _ in range(20):
        st = [x for x in o.list_sessions() if x.id == s.id][0].status
        if st == "finished":
            break
        time.sleep(0.1)
    # stopping a finished session is a no-op success
    r = o.stop_session(s.id)
    assert r["ok"] is True


def test_messaging(tmp_path):
    o = Orchestrator(str(tmp_path))
    m = o.send_message("coordinator", "Frontend", "add the header")
    assert o.inbox("frontend")[0].body == "add the header"
    # broadcast reaches every tentacle
    o.send_message("coordinator", "all", "broadcast hi")
    assert any(x.body == "broadcast hi" for x in o.inbox("backend"))
    # mark read removes it from the unread view
    assert o.mark_read(m.id)
    assert m.id not in [x.id for x in o.inbox("frontend", unread_only=True)]


def test_watch_once(tmp_path):
    import argparse
    from sentinel_suite_mcp.cli import cmd_orch_watch
    o = Orchestrator(str(tmp_path))
    o.send_message("boss", "frontend", "do the thing")
    ns = argparse.Namespace(tentacle="frontend", interval=0.1, on_message=None,
                            once=True, root=str(tmp_path))
    assert cmd_orch_watch(ns) == 0
    # the message was consumed (marked read)
    assert o.inbox("frontend", unread_only=True) == []


def test_team_dry_run(tmp_path):
    import argparse
    from sentinel_suite_mcp.cli import cmd_orch_team
    ns = argparse.Namespace(workers=["frontend", "backend"], coordinator="coordinator",
                            handler=None, dry_run=True, root=str(tmp_path))
    assert cmd_orch_team(ns) == 0
    ids = [t.id for t in Orchestrator(str(tmp_path)).list_tentacles()]
    assert {"coordinator", "frontend", "backend"} <= set(ids)
    # dry-run must not spawn any real sessions
    assert Orchestrator(str(tmp_path)).list_sessions() == []


def test_http_api(tmp_path):
    o = Orchestrator(str(tmp_path))
    o.scaffold()
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(o))
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        base = f"http://127.0.0.1:{port}"
        # dashboard
        html = urllib.request.urlopen(base + "/").read().decode()
        assert "Orchestrator" in html
        # create a tentacle via POST
        req = urllib.request.Request(
            base + "/api/tentacles", method="POST",
            data=json.dumps({"name": "api-tent", "scope": "x"}).encode(),
            headers={"content-type": "application/json"})
        created = json.loads(urllib.request.urlopen(req).read())
        assert created["id"] == "api-tent"
        # state reflects it
        state = json.loads(urllib.request.urlopen(base + "/api/state").read())
        assert any(t["id"] == "api-tent" for t in state["tentacles"])
    finally:
        httpd.shutdown()
        httpd.server_close()
