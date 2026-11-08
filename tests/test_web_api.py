"""HTTP protocol tests for sceneproof.web against a real server instance.

These exercise the same handler Vercel serverless wraps (api/index.py reuses H),
so validation/approval/heartbeat contracts are proven over real HTTP, not mocks.
"""
import json
import socket
import threading
import urllib.error
import urllib.request

import pytest

from sceneproof.scene import apply, generate
from sceneproof.web import BodyError, H, parse_intervention
from sceneproof.models import Intervention

from http.server import ThreadingHTTPServer


@pytest.fixture(scope="module")
def base_url():
    import sceneproof.web as web
    from sceneproof.engine import Engine
    web.ENG = Engine()  # fresh singleton: approval decisions must not leak between test modules
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{port}"
    srv.shutdown()


def get(url):
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def post(url, payload, expect_json=True):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


# ---------- unit-level validation (no server needed) ----------

def test_parse_intervention_verify_only():
    assert parse_intervention({"seed": 7}) is None


def test_parse_intervention_rejects_bad_action():
    with pytest.raises(BodyError, match="must be one of"):
        parse_intervention({"action": "explode", "object": "crate-b"})


def test_parse_intervention_rejects_out_of_range_delta():
    with pytest.raises(BodyError, match="dx must be between"):
        parse_intervention({"action": "move", "object": "crate-b", "dx": 5})


def test_parse_intervention_rejects_bad_kind():
    with pytest.raises(BodyError, match="kind must be one of"):
        parse_intervention({"action": "add", "object": "x1", "kind": "dragon"})


def test_parse_intervention_rejects_bad_id():
    with pytest.raises(BodyError, match="object id"):
        parse_intervention({"action": "move", "object": "../etc passwd"})


def test_parse_intervention_resize_requires_size_range():
    with pytest.raises(BodyError, match="w must be between"):
        parse_intervention({"action": "resize", "object": "crate-b", "w": 2.0})
    iv = parse_intervention({"action": "resize", "object": "crate-b", "w": 0.3})
    assert iv.w == 0.3 and iv.h == 0.0  # h omitted -> engine keeps original


# ---------- server contract ----------

def test_health(base_url):
    code, body = get(base_url + "/api/health")
    assert code == 200 and body == {"ok": True, "service": "sceneproof"}


def test_scene_and_seed_validation(base_url):
    code, body = get(base_url + "/api/scene?seed=7")
    assert code == 200 and len(body["scene"]["objects"]) == 6 and body["fingerprint"]
    code, body = get(base_url + "/api/scene?seed=zebra")
    assert code == 400 and "must be an integer" in body["error"]


def test_verify_only_run(base_url):
    code, body = post(base_url + "/api/run", {"seed": 7, "action": None})
    assert code == 200
    assert body["report"]["baseline"]["feasible"] is True
    assert "after_scene" not in body  # no intervention -> no counterfactual stage


def test_move_run_returns_exact_engine_stage(base_url):
    code, body = post(base_url + "/api/run", {"seed": 7, "action": "move", "object": "crate-b", "dx": 0.02, "dy": 0.0})
    assert code == 200
    iv = Intervention("move", "crate-b", dx=0.02)
    assert body["after_scene"] == apply(generate(7), iv).to_dict()
    assert body["report"]["effect"] is not None
    assert body["report"]["explanation_source"] in ("OFFLINE_REFERENCE",) or body["report"]["explanation_source"].startswith("META:")


def test_resize_run_changes_only_target_geometry(base_url):
    code, body = post(base_url + "/api/run", {"seed": 7, "action": "resize", "object": "crate-b", "w": 0.3, "h": 0.3})
    assert code == 200
    after = {o["id"]: o for o in body["after_scene"]["objects"]}
    assert after["crate-b"]["w"] == 0.3 and after["crate-b"]["h"] == 0.3
    assert after["shelf-1"]["w"] == 0.28  # untouched


def test_add_run_creates_object(base_url):
    code, body = post(base_url + "/api/run", {"seed": 7, "action": "add", "object": "cone-9", "kind": "cone", "w": 0.08, "h": 0.06, "dx": -0.2})
    assert code == 200  # non-sensitive kind runs without approval
    ids = [o["id"] for o in body["after_scene"]["objects"]]
    assert "cone-9" in ids and len(ids) == 7


def test_sensitive_interventions_require_approval_202(base_url):
    for payload in ({"seed": 7, "action": "remove", "object": "shelf-1"},
                    {"seed": 7, "action": "add", "object": "human-9", "kind": "human"}):
        code, body = post(base_url + "/api/run", payload)
        assert code == 202 and body["status"] == "APPROVAL_REQUIRED"


def test_approved_remove_runs_and_orphans_crate(base_url):
    code, body = post(base_url + "/api/run",
                      {"seed": 7, "action": "remove", "object": "shelf-1", "approver": "safety-lead", "approved": True})
    assert code == 200
    v = body["report"]["intervened"]
    assert v["feasible"] is False
    assert any("crate-a" in x["objects"] and x["rule"] in ("unsupported", "unstable_stack") for x in v["violations"])
    assert body["report"]["approvals"][0]["state"] == "APPROVED"


def test_validation_errors_are_400_with_actionable_messages(base_url):
    for payload, fragment in (
        ({"action": "teleport", "object": "x"}, "must be one of"),
        ({"action": "move", "object": "crate-b", "dx": "fast"}, "must be a number"),
        ({"action": "move", "object": "crate-b", "dy": 9}, "must be between"),
        ({"action": "add", "object": ""}, "is required for add"),
        ({"action": "resize", "object": "crate-b", "h": 0.9, "w": -1}, "must be between"),
    ):
        code, body = post(base_url + "/api/run", payload)
        assert code == 400 and fragment in body["error"], (payload, body)


def test_index_served_and_404(base_url):
    with urllib.request.urlopen(base_url + "/", timeout=5) as r:
        html = r.read().decode()
    assert "SceneProof" in html and "drag" in html
    code, body = get(base_url + "/definitely-missing.css")
    assert code == 404
