"""Orchestration: verify -> (approve) -> intervene -> re-verify -> explain -> ledger."""
from __future__ import annotations
from . import providers
from .constraints import verify
from .ledger import Ledger, ApprovalGate, ApprovalRequired
from .models import Intervention, Report
from .scene import apply

class Engine:
    def __init__(self):
        self.ledger = Ledger()
        self.gate = ApprovalGate(self.ledger)

    def run(self, scene, intervention: Intervention | None = None,
            approver: str | None = None, approved: bool = False) -> Report:
        base = verify(scene)
        self.ledger.append("verified", {"scene": scene.fingerprint(), "score": base.score, "feasible": base.feasible})
        report = Report(baseline=base)
        if intervention is not None:
            key = f"{scene.fingerprint()}:{intervention.action}:{intervention.object_id}"
            if intervention.sensitive:
                # Each sensitive run needs ITS OWN attributable human
                # decision. An earlier approval is history in the ledger —
                # it must never silently authorize a later request, or a
                # one-time grant becomes a permanent bypass.
                self.gate.request(key, True)
                report.approvals.append({"key": key, "state": "PENDING"})
                if not (approver and approved):
                    raise ApprovalRequired(f"sensitive intervention requires human approval ({key})")
                state = self.gate.decide(key, approver, True)
                report.approvals[-1]["state"] = state
            after_scene = apply(scene, intervention)
            after = verify(after_scene)
            self.ledger.append("counterfactual", {"action": intervention.action, "object": intervention.object_id,
                                                  "score": after.score, "feasible": after.feasible})
            report.intervened, report.effect = after, after.score - base.score
        report.explanation, report.explanation_source = providers.explain_verdict(report.to_dict())
        self.ledger.append("explained", {"source": report.explanation_source})
        report.ledger_head = self.ledger.head
        return report
