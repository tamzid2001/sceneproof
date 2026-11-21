"""Zero-dependency web app: stdlib http.server + static UI in web/.
Run: python -m sceneproof.web [--port 8000] | --smoke"""
from __future__ import annotations
import argparse, json, math
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from .engine import Engine
from .ledger import ApprovalRequired
from .models import Intervention, KINDS
from .scene import generate, supplied_scene

STATIC = Path(__file__).with_name("web")
TYPES = {".html": "text/html", ".css": "text/css", ".js": "text/javascript", ".png": "image/png"}

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _route(self) -> str:
        """Vercel rewrites /api/<ep> -> /api/index?ep=<ep>; map back to canonical paths."""
        from urllib.parse import urlparse, parse_qs
        u = urlparse(self.path)
        ep = parse_qs(u.query).get("ep", [None])[0]
        return {"health": "/api/health", "scene": "/api/scene", "run": "/api/run",
                "home": "/", "brand": "/brand.png", "favicon": "/favicon-32.png", "uiaudit": "/ui-audit.js", "css": "/app.css", "js": "/app.js"}.get(ep, u.path)
    def _send(self, code, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if self._route().startswith("/api/health"):
            return self._send(200, {"ok": True, "service": "sceneproof"})
        if self._route().startswith("/api/scene"):
            from urllib.parse import urlparse, parse_qs
            seed = int(parse_qs(urlparse(self.path).query).get("seed", ["7"])[0])
            s = generate(seed)
            return self._send(200, {"scene": s.to_dict(), "fingerprint": s.fingerprint(), "source": "FIXTURE"})
        route = self._route(); name = "index.html" if route in ("/", "") else route.lstrip("/").split("?")[0]
        f = STATIC / name
        if f.is_file() and f.suffix in TYPES: return self._send(200, f.read_bytes(), TYPES[f.suffix])
        return self._send(404, {"error": "not found"})
    def do_POST(self):
        route = self._route()
        if route not in {"/api/run", "/api/scene"}:
            return self._send(404, {"error": "not found"})
        try:
            size = int(self.headers.get("Content-Length", 0))
            if not 0 <= size <= 65_536:
                return self._send(413, {"error": "Scene input exceeds 64 KiB."})
            body = json.loads(self.rfile.read(size) or b"{}")
            if not isinstance(body, dict):
                raise ValueError("Use a JSON object.")
            if route == "/api/scene":
                scene = supplied_scene(body)
                return self._send(200, {"scene": scene.to_dict(),
                                        "fingerprint": scene.fingerprint(), "source": "USER_SUPPLIED"})
            if "scene" in body and "seed" in body:
                raise ValueError("Send either a scene object or a fixture seed.")
            source = "USER_SUPPLIED" if "scene" in body else "FIXTURE"
            scene = supplied_scene(body["scene"]) if "scene" in body else generate(int(body.get("seed", 7)))
            iv = None
            if body.get("action"):
                action = body["action"]
                object_id = str(body.get("object", "crate-b"))
                if action not in {"move", "remove", "resize", "add"}:
                    raise ValueError("Choose a supported intervention.")
                kind = body.get("kind", "crate") if action == "add" else scene.get(object_id).kind
                if kind not in KINDS:
                    raise ValueError("Choose a supported object kind.")
                if not object_id or len(object_id) > 80 or (action == "add" and any(o.id == object_id for o in scene.objects)):
                    raise ValueError("Choose a distinct, valid object identifier.")
                dx, dy, width, height = (float(body.get(field, 0)) for field in ("dx", "dy", "w", "h"))
                if not (math.isfinite(dx) and math.isfinite(dy) and -2 <= dx <= 2 and -2 <= dy <= 2):
                    raise ValueError("Choose finite offsets between −2 and 2.")
                if not (0 <= width <= 2 and 0 <= height <= 2):
                    raise ValueError("Choose finite dimensions between 0 and 2.")
                iv = Intervention(action, object_id, dx, dy, width, height, kind)
            engine = Engine()
            rep = engine.run(scene, iv, approver=body.get("approver") or None,
                          approved=body.get("approved") is True, explain=body.get("explain", True) is True)
            return self._send(200, {"report": rep.to_dict(), "scene": scene.to_dict(),
                                    "chain_valid": engine.ledger.verify_chain(),
                                    "fingerprint": scene.fingerprint(), "source": source})
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
