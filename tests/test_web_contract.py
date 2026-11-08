"""Web API contract tests — the approval gate must not be client-trusting,
and every documented intervention must actually do what it says."""
import json
import threading
import urllib.request
import urllib.error

import pytest

from sceneproof.models import Intervention, Scene, SceneObject


def _post(port, body):
    req = urllib.request.Request(f"http://127.0.0.1:{port}/api/run",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)


@pytest.fixture()
def server():
    from http.server import ThreadingHTTPServer
    from sceneproof import web
    srv = ThreadingHTTPServer(("127.0.0.1", 0), web.H)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield port
    srv.shutdown(); srv.server_close()


def test_an_earlier_approval_never_authorizes_a_later_request(server):
    """A one-time human grant must not become a permanent bypass: the
    shared process-wide engine remembered the decision and let every
    later identical request run unapproved."""
    body = {"seed": 7, "action": "remove", "object": "shelf-1"}
    status, first = _post(server, {**body, "approver": "safety-lead", "approved": True})
    assert status == 200 and first["report"]["approvals"][0]["state"] == "APPROVED"
    # a second request with NO approval at all must be refused again
    status, second = _post(server, body)
    assert status == 202 and second["status"] == "APPROVAL_REQUIRED"
    # ...and an approval without a name must be refused too
    status, third = _post(server, {**body, "approved": True})
    assert status == 202 and third["status"] == "APPROVAL_REQUIRED"
    # the ledger kept both decisions as history
    status, again = _post(server, {**body, "approver": "another-lead", "approved": True})
    assert status == 200 and again["chain_valid"] is True


def test_moving_a_human_is_gated_even_when_the_client_sends_no_kind(server, monkeypatch):
    """The approval gate must resolve the target's kind from the scene
    itself. A client that forgets to send `kind` (as the shipped UI did)
    must NOT be able to move a human unapproved."""
    human_scene = Scene("demo-warehouse", (
        SceneObject("human-1", "human", 0.50, 0.0, 0.06, 0.30),
        SceneObject("crate-b", "crate", 0.40, 0.0, 0.14, 0.14),
    ), seed=7)
    monkeypatch.setattr("sceneproof.web.generate", lambda seed=7: human_scene)
    status, body = _post(server, {"seed": 7, "action": "move", "object": "human-1",
                                  "dx": 0.05, "dy": 0, "approver": "safety-lead", "approved": True})
    # approved=True, so the gate opens — but the point is the gate ENGAGED at all
    assert status == 200 and body["report"]["approvals"], "the human move must engage the gate"
    assert body["report"]["approvals"][0]["key"].endswith(":move:human-1")


def test_moving_a_human_without_approval_is_refused(server, monkeypatch):
    human_scene = Scene("demo-warehouse", (
        SceneObject("human-1", "human", 0.50, 0.0, 0.06, 0.30),
        SceneObject("crate-b", "crate", 0.40, 0.0, 0.14, 0.14),
    ), seed=7)
    monkeypatch.setattr("sceneproof.web.generate", lambda seed=7: human_scene)
    status, body = _post(server, {"seed": 7, "action": "move", "object": "human-1", "dx": 0.05})
    assert status == 202 and body["status"] == "APPROVAL_REQUIRED"


def test_moving_a_plain_crate_is_not_gated(server):
    status, body = _post(server, {"seed": 7, "action": "move", "object": "crate-b", "dx": 0.05})
    assert status == 200 and body["report"]["approvals"] == []


def test_resize_actually_resizes_through_the_web_api(server):
    """The web layer used to drop the requested w/h, so `resize` silently
    performed a no-op. Growing crate-b into barrel-1 must now produce a
    real interpenetration violation in the counterfactual verdict."""
    status, body = _post(server, {"seed": 7, "action": "resize", "object": "crate-b", "w": 0.25, "h": 0.14})
    assert status == 200
    intervened = body["report"]["intervened"]
    assert intervened is not None, "the resize must produce a counterfactual verdict"
    rules = {v["rule"] for v in intervened["violations"]}
    assert "interpenetration" in rules, "a wider crate-b now overlaps barrel-1 — the resize took effect"
    assert set(intervened["violations"][0]["objects"]) >= {"crate-b", "barrel-1"}


def test_a_resize_that_fits_changes_nothing_unexpectedly(server):
    status, body = _post(server, {"seed": 7, "action": "resize", "object": "crate-b", "w": 0.12, "h": 0.12})
    assert status == 200
    assert body["report"]["intervened"]["feasible"] is True


def test_unknown_action_is_rejected(server):
    status, body = _post(server, {"seed": 7, "action": "teleport", "object": "crate-b"})
    assert status == 400 and "action must be one of move/remove/resize/add" in body["error"]


def test_unknown_object_is_rejected(server):
    status, body = _post(server, {"seed": 7, "action": "move", "object": "ghost-9"})
    assert status == 400 and "no object" in body["error"] and "ghost-9" in body["error"]


def test_add_with_an_unknown_kind_is_rejected(server):
    status, body = _post(server, {"seed": 7, "action": "add", "object": "new-crate", "kind": "ghost"})
    assert status == 400 and "kind must be one of" in body["error"]


def test_add_with_a_valid_kind_works(server):
    status, body = _post(server, {"seed": 7, "action": "add", "object": "new-crate",
                                  "kind": "crate", "dx": 0.0, "dy": 0.0, "w": 0.08, "h": 0.08})
    assert status == 200 and body["report"]["intervened"] is not None


def test_adding_a_human_is_gated(server):
    status, body = _post(server, {"seed": 7, "action": "add", "object": "visitor-1",
                                  "kind": "human", "dy": 0.0, "w": 0.05, "h": 0.3})
    assert status == 202 and body["status"] == "APPROVAL_REQUIRED"


def test_out_of_stage_sizes_are_rejected(server):
    for size_field in ("w", "h"):
        status, body = _post(server, {"seed": 7, "action": "resize", "object": "crate-b", size_field: 5.0})
        assert status == 400 and "must be between 0.01 and 1.0" in body["error"]


def test_negative_sizes_are_rejected(server):
    status, body = _post(server, {"seed": 7, "action": "resize", "object": "crate-b", "w": -1.0})
    assert status == 400 and "must be between 0.01 and 1.0" in body["error"]


def test_sensitivity_depends_on_the_target_kind_not_the_client():
    """Model-level documentation of why the server resolves the kind."""
    assert Intervention("move", "human-1", kind="human").sensitive is True
    assert Intervention("resize", "vehicle-1", kind="vehicle").sensitive is True
    assert Intervention("move", "human-1").sensitive is False, "a bare Intervention cannot know the kind"
    assert Intervention("move", "crate-b", kind="crate").sensitive is False


def test_removal_is_gated_regardless_of_kind(server):
    status, body = _post(server, {"seed": 7, "action": "remove", "object": "shelf-1"})
    assert status == 202 and body["status"] == "APPROVAL_REQUIRED"
    status, body = _post(server, {"seed": 7, "action": "remove", "object": "shelf-1",
                                  "approver": "safety-lead", "approved": True})
    assert status == 200 and body["report"]["approvals"][0]["state"] == "APPROVED"
