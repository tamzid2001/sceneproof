"""Zero-dependency web app: stdlib http.server + static UI in web/.
Run: python -m sceneproof.web [--port 8000] | --smoke"""
from __future__ import annotations
import argparse, json, re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from .engine import Engine
from .ledger import ApprovalRequired
from .models import KINDS, Intervention
from .scene import apply, generate

STATIC = Path(__file__).with_name("web")
ENG = Engine()
TYPES = {".html": "text/html", ".css": "text/css", ".js": "text/javascript"}
ID_RE = re.compile(r"[A-Za-z0-9._-]{1,64}")


class BodyError(ValueError):
    """Request validation failure surfaced to the client as an honest 400 message."""


def parse_intervention(body, scene=None) -> Intervention | None:
    """Validate a request body into an Intervention, or raise BodyError honestly.

    Contract: action ∈ {move, remove, resize, add}; dx/dy ∈ [-1,1]; resize/add
    sizes w/h ∈ [0.01,1]; object ids 1..64 chars of [A-Za-z0-9._-]; kind ∈ KINDS.
    No silent fixups — anything ambiguous is rejected, not repaired.

    For move/remove/resize the object's kind is resolved from the SCENE, never
    from the request: `Intervention.sensitive` decides the approval gate from
    `kind`, so a client that omits (or lies about) `kind` must not be able to
    move a human or a vehicle unapproved. `kind` is therefore only meaningful
    for `add`, where the object does not exist yet.
    """
    if not isinstance(body, dict):
        raise BodyError("request body must be a JSON object")
    action = str(body.get("action") or "").strip()
    if not action:
        return None
    if action not in {"move", "remove", "resize", "add"}:
        raise BodyError(f"action must be one of move/remove/resize/add, got: {action!r}")

    def num(name: str, default: float = 0.0, lo: float = -1.0, hi: float = 1.0) -> float:
        raw = body.get(name, default)
        try:
            v = float(raw)
        except (TypeError, ValueError):
            raise BodyError(f"{name} must be a number, got: {raw!r}") from None
        if not lo <= v <= hi:
            raise BodyError(f"{name} must be between {lo} and {hi}, got: {v}")
        return round(v, 4)

    dx, dy = num("dx"), num("dy")
    oid = str(body.get("object", "")).strip()
    if action == "add":
        if not ID_RE.fullmatch(oid):
            raise BodyError("object id (1-64 chars of [A-Za-z0-9._-]) is required for add")
        kind = str(body.get("kind", "crate")).strip()
        if kind not in KINDS:
            raise BodyError(f"kind must be one of {sorted(KINDS)}, got: {kind!r}")
        w = num("w", default=0.1, lo=0.01, hi=1.0)
        h = num("h", default=0.1, lo=0.01, hi=1.0)
    else:
        if not ID_RE.fullmatch(oid):
            raise BodyError("object id (1-64 chars of [A-Za-z0-9._-]) is required")
        if scene is None:
            raise BodyError("server must resolve the target object from the scene")
        try:
            kind = scene.get(oid).kind
        except KeyError:
            raise BodyError(f"no object {oid!r} in scene {scene.id!r}") from None
        has_w, has_h = body.get("w") not in (None, ""), body.get("h") not in (None, "")
        if action == "resize" and not (has_w or has_h):
            raise BodyError("resize requires w and/or h to actually change geometry")
        w = num("w", lo=0.01, hi=1.0) if has_w else 0.0
        h = num("h", lo=0.01, hi=1.0) if has_h else 0.0
    if action == "resize" and w == 0.0 and h == 0.0:
        raise BodyError("resize must not be a no-op")
    return Intervention(action, oid, dx=dx, dy=dy, w=w, h=h, kind=kind)


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _route(self) -> str:
        """Vercel rewrites /api/<ep> -> /api/index?ep=<ep>; map back to canonical paths."""
        from urllib.parse import urlparse, parse_qs
        u = urlparse(self.path)
        ep = parse_qs(u.query).get("ep", [None])[0]
        return {"health": "/api/health", "scene": "/api/scene", "run": "/api/run",
                "home": "/", "css": "/app.css", "js": "/app.js"}.get(ep, u.path)

    def _send(self, code, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self._route().startswith("/api/health"):
            return self._send(200, {"ok": True, "service": "sceneproof"})
        if self._route().startswith("/api/scene"):
            from urllib.parse import urlparse, parse_qs
            raw = parse_qs(urlparse(self.path).query).get("seed", ["7"])[0]
            try:
                seed = int(raw)
            except ValueError:
                return self._send(400, {"error": f"seed must be an integer, got: {raw!r}"})
            s = generate(seed)
            return self._send(200, {"scene": s.to_dict(), "fingerprint": s.fingerprint()})
        route = self._route()
        name = "index.html" if route in ("/", "") else route.lstrip("/").split("?")[0]
        f = STATIC / name
        if f.is_file() and f.suffix in TYPES:
            return self._send(200, f.read_bytes(), TYPES[f.suffix])
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        if not self._route().startswith("/api/run"):
            return self._send(404, {"error": "not found"})
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            scene = generate(int(body.get("seed", 7)))
            iv = parse_intervention(body, scene)
            rep = ENG.run(scene, iv, approver=body.get("approver") or None,
                          approved=bool(body.get("approved")))
            out = {"report": rep.to_dict(), "scene": scene.to_dict(),
                   "chain_valid": ENG.ledger.verify_chain()}
            if rep.intervened is not None:
                out["after_scene"] = apply(scene, iv).to_dict()
            return self._send(200, out)
        except ApprovalRequired as e:
            return self._send(202, {"status": "APPROVAL_REQUIRED", "detail": str(e)})
        except BodyError as e:
            return self._send(400, {"error": str(e)})
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
        assert h["ok"] and "SceneProof" in page
        print("smoke ok: health + UI served")
        srv.shutdown()
        return 0
    print(f"SceneProof on http://127.0.0.1:{a.port}")
    srv.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
