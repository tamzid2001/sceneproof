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
