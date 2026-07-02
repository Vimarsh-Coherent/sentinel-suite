"""Local API + dashboard for the Sentinel Suite Orchestrator (stdlib only).

Mirrors Octogent's local server role (default port 8787): a JSON API plus a
single-page HTML dashboard to view/create tentacles and start/stop sessions.

Run:  sentinel-suite orchestrate serve   (or: python -m sentinel_suite_mcp.orchestrator_server)
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from .orchestrator import Orchestrator

DASHBOARD = """<!doctype html>
<html><head><meta charset="utf-8"><title>Sentinel Suite Orchestrator</title>
<style>
 body{font-family:system-ui,Segoe UI,Arial;margin:0;background:#0f1115;color:#e6e6e6}
 header{padding:14px 24px;background:#161a22;border-bottom:1px solid #262b36;display:flex;align-items:center;gap:18px;flex-wrap:wrap}
 h1{font-size:17px;margin:0}
 .stat{font-size:12px;color:#9aa4b2}.stat b{color:#e6e6e6;font-size:15px}
 main{display:grid;grid-template-columns:1fr 1fr;gap:16px;padding:24px}
 .card{background:#161a22;border:1px solid #262b36;border-radius:10px;padding:16px}
 h2{font-size:13px;color:#9aa4b2;margin:0 0 12px;text-transform:uppercase;letter-spacing:.5px}
 .item{border:1px solid #262b36;border-radius:8px;padding:10px;margin-bottom:8px}
 .id{font-weight:600}
 .muted{color:#8892a0;font-size:12px}
 .dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px}
 .on{background:#5ad19a;box-shadow:0 0 8px #5ad19a}.off{background:#4b5565}
 .run{color:#5ad19a}.fin{color:#8892a0}
 .msg{border-left:3px solid #2563eb;padding:6px 10px;margin-bottom:6px;background:#12161f;border-radius:0 6px 6px 0}
 .bcast{border-left-color:#d19a5a}
 input,button{background:#0f1115;color:#e6e6e6;border:1px solid #2a3140;border-radius:6px;padding:8px;font-size:13px}
 button{cursor:pointer;background:#2563eb;border-color:#2563eb}
 form{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}
</style></head><body>
<header>
 <h1>🐙 Sentinel Suite — Team</h1>
 <span class="stat" id="proj"></span>
 <span class="stat"><b id="nw">0</b> members</span>
 <span class="stat"><b id="nr">0</b> working</span>
 <span class="stat"><b id="nm">0</b> messages</span>
</header>
<main>
 <div class="card"><h2>Team members</h2><div id="team"></div>
  <form onsubmit="return newTentacle(event)">
   <input id="tname" placeholder="new member name" required>
   <input id="tscope" placeholder="scope (optional)">
   <button>Add</button></form></div>
 <div class="card"><h2>Conversation</h2><div id="messages"></div>
  <form onsubmit="return sendMsg(event)">
   <input id="mfrom" placeholder="from" required style="width:90px">
   <input id="mto" placeholder="to / all" required style="width:90px">
   <input id="mbody" placeholder="message" required style="flex:1">
   <button>Send</button></form></div>
</main>
<script>
function esc(s){return (s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}
async function load(){
 const s = await (await fetch('/api/state')).json();
 proj.textContent = s.project;
 const running = s.sessions.filter(x=>x.status==='running');
 nw.textContent = s.tentacles.length; nr.textContent = running.length; nm.textContent = (s.messages||[]).length;
 // team members: each tentacle + whether it has a running session (its worker)
 team.innerHTML = s.tentacles.map(t=>{
   const mine = s.sessions.filter(x=>x.tentacle===t.id);
   const live = mine.some(x=>x.status==='running');
   const last = (s.messages||[]).filter(m=>m.recipient===t.id||m.sender===t.id).slice(-1)[0];
   return `<div class="item"><div class="id"><span class="dot ${live?'on':'off'}"></span>${esc(t.id)}
     <span class="muted">${live?'working':'idle'}</span></div>
     <div class="muted">${esc(t.scope||'')}</div>
     ${last?`<div class="muted">last: ${esc(last.sender)}→${esc(last.recipient)}: ${esc(last.body).slice(0,60)}</div>`:''}
     ${live?mine.filter(x=>x.status==='running').map(x=>`<button onclick="stop('${x.id}')">stop</button>`).join(''):''}</div>`;
 }).join('')||'<div class="muted">no members yet — add one or run: orchestrate team frontend backend</div>';
 // conversation, newest first
 messages.innerHTML = (s.messages||[]).slice().reverse().map(m=>
   `<div class="msg ${m.recipient==='all'?'bcast':''}"><div class="id">${esc(m.sender)} → ${esc(m.recipient)}</div><div>${esc(m.body)}</div></div>`
 ).join('')||'<div class="muted">no messages yet</div>';
}
async function sendMsg(e){e.preventDefault();
 await fetch('/api/messages',{method:'POST',headers:{'content-type':'application/json'},
  body:JSON.stringify({sender:mfrom.value,recipient:mto.value,body:mbody.value})}); mbody.value=''; load(); return false;}
async function newTentacle(e){e.preventDefault();
 await fetch('/api/tentacles',{method:'POST',headers:{'content-type':'application/json'},
  body:JSON.stringify({name:tname.value,scope:tscope.value})}); tname.value='';tscope.value=''; load(); return false;}
async function stop(id){await fetch('/api/sessions/'+id+'/stop',{method:'POST'}); load();}
load(); setInterval(load, 2000);
</script></body></html>"""


def make_handler(orch: Orchestrator):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):  # quiet
            pass

        def _send(self, code: int, body: bytes, ctype: str):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj, code: int = 200):
            self._send(code, json.dumps(obj).encode("utf-8"), "application/json")

        def _body(self) -> dict:
            n = int(self.headers.get("Content-Length", 0) or 0)
            if not n:
                return {}
            try:
                return json.loads(self.rfile.read(n).decode("utf-8") or "{}")
            except Exception:
                return {}

        def do_GET(self):
            path = urlparse(self.path).path
            if path in ("/", "/index.html"):
                self._send(200, DASHBOARD.encode("utf-8"), "text/html; charset=utf-8")
            elif path == "/api/state":
                self._json(orch.summary())
            elif path == "/api/tentacles":
                self._json([t.__dict__ for t in orch.list_tentacles()])
            elif path == "/api/sessions":
                self._json([s.__dict__ for s in orch.list_sessions()])
            elif path == "/api/messages":
                q = parse_qs(urlparse(self.path).query)
                to = (q.get("to") or [None])[0]
                msgs = orch.inbox(to) if to else orch._all_messages()
                self._json([m.__dict__ for m in msgs])
            else:
                self._json({"error": "not found"}, 404)

        def do_POST(self):
            path = urlparse(self.path).path
            body = self._body()
            if path == "/api/tentacles":
                t = orch.create_tentacle(body.get("name", ""), body.get("description", ""),
                                         body.get("scope", ""))
                self._json(t.__dict__, 201)
            elif path == "/api/sessions":
                s = orch.spawn_session(body.get("tentacle", ""), body.get("command", ""))
                self._json(s.__dict__, 201)
            elif path.startswith("/api/sessions/") and path.endswith("/stop"):
                sid = path[len("/api/sessions/"):-len("/stop")]
                self._json(orch.stop_session(sid))
            elif path == "/api/messages":
                m = orch.send_message(body.get("sender", ""), body.get("recipient", ""),
                                      body.get("body", ""), body.get("subject", ""))
                self._json(m.__dict__, 201)
            else:
                self._json({"error": "not found"}, 404)

    return Handler


def serve(host: str = "127.0.0.1", port: int = 8787, root: str | None = None) -> int:
    orch = Orchestrator(root)
    orch.scaffold()
    httpd = ThreadingHTTPServer((host, port), make_handler(orch))
    print(f"Sentinel Suite Orchestrator: http://{host}:{port}  (project: {orch.root.name})")
    print("Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(serve())
