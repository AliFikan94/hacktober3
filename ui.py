#!/usr/bin/env python3
"""Tiny local web UI for Sloth Tidy. Run: python ui.py  then open http://127.0.0.1:8765"""
import json
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import sloth

HOST = "http://localhost:11434"
STATE = {"folder": None, "moves": []}

PAGE = """<!doctype html><meta charset=utf-8><title>Sloth Tidy</title>
<style>body{font:16px system-ui;max-width:760px;margin:2rem auto;padding:0 1rem;color:#222}
input,button,select{font:inherit;padding:.5rem;margin:.2rem 0}input[type=text]{width:100%;box-sizing:border-box}
button{cursor:pointer}table{width:100%;border-collapse:collapse;margin-top:1rem}
td{padding:.4rem;border-bottom:1px solid #ddd}.arrow{color:#888}#msg{margin-top:1rem;color:#555}
h1 small{font-size:.5em;color:#888}</style>
<h1>Sloth Tidy <small>runs on your own local model</small></h1>
<label>Folder to tidy<input id=folder type=text placeholder="C:\\Users\\HP\\mini"></label>
<label>Model <input id=model value="gemma3:1b"></label>
<label>Max files <input id=limit type=number value=10 style="width:5rem"></label><br>
<button onclick="go('plan')">1. Preview</button>
<button onclick="go('apply')">2. Apply</button>
<button onclick="go('undo')">Undo</button>
<div id=msg></div><table id=t></table>
<script>
async function go(a){
  const m=document.getElementById('msg'),t=document.getElementById('t');
  m.textContent=a=='plan'?'Thinking... small models on CPU can take a while per file.':'Working...';
  const r=await fetch('/api/'+a,{method:'POST',body:JSON.stringify({folder:folder.value,model:model.value,limit:+limit.value})});
  const d=await r.json();
  m.textContent=d.message||d.error||'';
  t.innerHTML=(d.moves||[]).map(x=>`<tr><td>${x[0]}</td><td class=arrow>&rarr;</td><td><b>${x[1]}</b></td></tr>`).join('');
}
</script>"""


def make_classify(model, notes):
    state = {"ok": sloth.server_up(HOST)}
    if not state["ok"]:
        notes.append("Ollama not reachable, used extension rules.")

    def classify(p):
        if state["ok"]:
            res = sloth.ask_model(p, HOST, model, 120, sloth.rule_category(p))
            if res:
                return res
            state["ok"] = False
            notes.append("Model failed, fell back to extension rules for the rest.")
        return sloth.rule_category(p), sloth.slugify(p.stem) or "file"
    return classify


def handle(action, req):
    folder = Path(req.get("folder", "")).expanduser()
    if not folder.is_dir():
        return {"error": f"Not a folder: {folder}"}
    if action == "plan":
        notes = []
        moves = sloth.plan(folder, make_classify(req.get("model") or "gemma3:1b", notes), req.get("limit") or None)
        STATE.update(folder=folder, moves=moves)
        rel = [[s.name, str(d.relative_to(folder))] for s, d in moves]
        return {"moves": rel, "message": " ".join([f"{len(moves)} files planned. Nothing moved yet."] + notes)}
    if action == "apply":
        if STATE["folder"] != folder or not STATE["moves"]:
            return {"error": "Click Preview first."}
        sloth.apply(STATE["moves"], folder)
        n = len(STATE["moves"])
        STATE["moves"] = []
        return {"message": f"Moved {n} files. Click Undo to revert."}
    if action == "undo":
        try:
            sloth.undo(folder)
        except SystemExit as e:
            return {"error": str(e)}
        return {"message": "Undone. Files are back where they were."}
    return {"error": "unknown action"}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._send(200, PAGE.encode(), "text/html; charset=utf-8")

    def do_POST(self):
        req = json.loads(self.rfile.read(int(self.headers["Content-Length"])) or b"{}")
        try:
            out = handle(self.path.rsplit("/", 1)[-1], req)
        except Exception as e:
            out = {"error": f"{type(e).__name__}: {e}"}
        self._send(200, json.dumps(out).encode(), "application/json")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    srv = HTTPServer(("127.0.0.1", port), H)  # localhost only
    print(f"Open http://127.0.0.1:{port}  (Ctrl+C to stop)")
    webbrowser.open(f"http://127.0.0.1:{port}")
    srv.serve_forever()
