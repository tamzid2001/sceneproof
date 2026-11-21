import pytest
from sceneproof.constraints import verify
from sceneproof.engine import Engine
from sceneproof.ledger import Ledger, ApprovalRequired
from sceneproof.models import Intervention, Scene, SceneObject
from sceneproof.scene import generate, apply

def test_generated_scene_is_feasible():
    v = verify(generate())
    assert v.feasible and v.score == 100 and not v.violations

@pytest.mark.parametrize("seed", [1, 2, 3, 42])
def test_seeds_deterministic_and_feasible(seed):
    assert generate(seed).to_dict() == generate(seed).to_dict()
    assert verify(generate(seed)).feasible

def test_interpenetration_rejected():
    s = Scene("t", (SceneObject("a", "crate", .1, 0, .2, .2), SceneObject("b", "crate", .15, .05, .2, .2)))
    v = verify(s)
    assert not v.feasible and any(x.rule == "interpenetration" for x in v.violations)

def test_floating_object_rejected():
    s = Scene("t", (SceneObject("a", "crate", .1, .5, .2, .2),))
    assert any(x.rule == "unsupported" for x in verify(s).violations)

def test_out_of_bounds_rejected():
    s = Scene("t", (SceneObject("a", "crate", .95, 0, .2, .2),))
    assert any(x.rule == "out_of_bounds" for x in verify(s).violations)

def test_removing_shelf_orphans_crate():
    after = apply(generate(), Intervention("remove", "shelf-1"))
    v = verify(after)
    assert not v.feasible and any("crate-a" in x.objects for x in v.violations)

def test_counterfactual_effect_is_signed_difference():
    rep = Engine().run(generate(), Intervention("move", "crate-b", dx=0.6, dy=0.4))
    assert rep.effect == pytest.approx(rep.intervened.score - rep.baseline.score)
    assert rep.effect < 0  # moved crate now floats

def test_ledger_chain_verifies_and_detects_tamper():
    led = Ledger(); led.append("a", {"x": 1}); led.append("b", {"y": 2})
    assert led.verify_chain()
    led.entries[0]["payload"]["x"] = 999
    assert not led.verify_chain()

def test_sensitive_intervention_needs_approval():
    with pytest.raises(ApprovalRequired):
        Engine().run(generate(), Intervention("remove", "shelf-1"))
    rep = Engine().run(generate(), Intervention("remove", "shelf-1"), approver="safety-lead", approved=True)
    assert rep.approvals and rep.approvals[0]["state"] == "APPROVED"

def test_rejected_approval_blocks():
    with pytest.raises(ApprovalRequired):
        Engine().run(generate(), Intervention("remove", "shelf-1"), approver="safety-lead", approved=False)

def test_offline_explanation_is_honestly_labelled():
    rep = Engine().run(generate())
    assert rep.explanation_source == "OFFLINE_REFERENCE"
    assert "FEASIBLE" in rep.explanation

def test_provider_blocks_without_credentials(monkeypatch):
    from sceneproof import providers
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    with pytest.raises(providers.BlockedCredentials):
        providers.segment_scene("https://example.com/x.png")

def test_web_smoke():
    from sceneproof.web import main
    assert main(["--smoke", "--port", "8765"]) == 0


def test_counterfactual_geometry_matches_the_verdict(monkeypatch):
    from sceneproof import providers

    def fail(_):
        raise AssertionError("This verification should stay local")

    monkeypatch.setattr(providers, "explain_verdict", fail)
    scene = generate()
    report = Engine().run(scene, Intervention("resize", "crate-b", w=.9, h=.32), explain=False)
    assert report.intervened_scene.get("crate-b").w == .9
    assert scene.get("crate-b").w == .14
    assert report.intervened == verify(report.intervened_scene)
    assert report.to_dict()["intervened_scene"] == report.intervened_scene.to_dict()


def test_web_counterfactual_requires_request_approval_and_preserves_resize():
    import json
    import threading
    import urllib.error
    import urllib.request
    from http.server import ThreadingHTTPServer
    from sceneproof.web import H

    with ThreadingHTTPServer(("127.0.0.1", 0), H) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        origin = f"http://127.0.0.1:{server.server_address[1]}"

        def request(body):
            data = json.dumps({"explain": False, **body}).encode()
            req = urllib.request.Request(origin + "/api/run", data=data, headers={"Content-Type": "application/json"})
            try:
                response = urllib.request.urlopen(req, timeout=4)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                return response.status, json.load(response)

        try:
            code, body = request({"action": "resize", "object": "crate-b", "w": .9, "h": .32})
            assert code == 200
            box = next(o for o in body["report"]["intervened_scene"]["objects"] if o["id"] == "crate-b")
            assert (box["w"], box["h"]) == (.9, .32)
            assert request({"action": "resize", "h": "NaN"})[0] == 400
            assert request({"action": "remove", "object": "shelf-1", "approver": "reviewer", "approved": True})[0] == 200
            assert request({"action": "remove", "object": "shelf-1"})[0] == 202
            assert request({"action": "remove", "object": "shelf-1", "approver": "reviewer", "approved": "false"})[0] == 202
        finally:
            server.shutdown()
            thread.join(timeout=3)
