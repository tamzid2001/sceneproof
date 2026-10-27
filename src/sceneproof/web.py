"""Zero-dependency web app: stdlib http.server + static UI in web/.
Run: python -m sceneproof.web [--port 8000] | --smoke"""
from __future__ import annotations
import argparse, json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from .engine import Engine
from .ledger import ApprovalRequired
from .models import Intervention
from .scene import generate

STATIC = Path(__file__).with_name("web")
ENG = Engine()
TYPES = {".html": "text/html", ".css": "text/css", ".js": "text/javascript"}

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, code, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if self.path.startswith("/api/health"):
            return self._send(200, {"ok": True, "service": "sceneproof"})
        if self.path.startswith("/api/scene"):
            seed = int(self.path.split("seed=")[-1]) if "seed=" in self.path else 7
            s = generate(seed); return self._send(200, {"scene": s.to_dict(), "fingerprint": s.fingerprint()})
        name = "index.html" if self.path in ("/", "") else self.path.lstrip("/").split("?")[0]
        f = STATIC / name
        if f.is_file() and f.suffix in TYPES: return self._send(200, f.read_bytes(), TYPES[f.suffix])
        return self._send(404, {"error": "not found"})
    def do_POST(self):
        if not self.path.startswith("/api/run"): return self._send(404, {"error": "not found"})
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            scene = generate(int(body.get("seed", 7)))
            iv = None
            if body.get("action"):
                iv = Intervention(body["action"], body.get("object", "crate-b"),
                                  dx=float(body.get("dx", 0)), dy=float(body.get("dy", 0)),
                                  kind=body.get("kind", "crate"))
            rep = ENG.run(scene, iv, approver=body.get("approver") or None,
                          approved=bool(body.get("approved")))
            return self._send(200, {"report": rep.to_dict(), "scene": scene.to_dict(),
                                    "chain_valid": ENG.ledger.verify_chain()})
        except ApprovalRequired as e:
            return self._send(202, {"status": "APPROVAL_REQUIRED", "detail": str(e)})
        except Exception as e:  # keep the demo honest, never 500 silently
            return self._send(400, {"error": str(e)})

def main(argv=None) -> int:
    p = argparse.ArgumentParser(); p.add_argument("--port", type=int, default=8000)
    p.add_argument("--smoke", action="store_true"); a = p.parse_args(argv)
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), H)
    if a.smoke:
        import threading, urllib.request
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        h = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{a.port}/api/health", timeout=5).read())
        page = urllib.request.urlopen(f"http://127.0.0.1:{a.port}/", timeout=5).read().decode()
        assert h["ok"] and "SceneProof" in page; print("smoke ok: health + UI served"); srv.shutdown(); return 0
    print(f"SceneProof on http://127.0.0.1:{a.port}"); srv.serve_forever(); return 0

if __name__ == "__main__":
    raise SystemExit(main())
