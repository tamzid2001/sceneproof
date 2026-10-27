"""Append-only, hash-chained audit ledger + human approval gate."""
from __future__ import annotations
import hashlib, json, time

class Ledger:
    def __init__(self): self.entries: list[dict] = []
    @property
    def head(self) -> str: return self.entries[-1]["hash"] if self.entries else "GENESIS"
    def append(self, event: str, payload: dict) -> dict:
        body = {"i": len(self.entries), "ts": round(time.time(), 3), "event": event,
                "payload": payload, "prev": self.head}
        body["hash"] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        self.entries.append(body)
        return body
    def verify_chain(self) -> bool:
        prev = "GENESIS"
        for e in self.entries:
            if e["prev"] != prev: return False
            body = {k: e[k] for k in ("i", "ts", "event", "payload", "prev")}
            if hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest() != e["hash"]: return False
            prev = e["hash"]
        return True

class ApprovalRequired(Exception): pass

class ApprovalGate:
    """Sensitive interventions need an explicit human decision, recorded in the ledger."""
    def __init__(self, ledger: Ledger): self.ledger, self.decisions = ledger, {}
    def request(self, key: str, sensitive: bool) -> str:
        if not sensitive: return "NOT_REQUIRED"
        self.ledger.append("approval_requested", {"key": key})
        return self.decisions.get(key, "PENDING")
    def decide(self, key: str, approver: str, approved: bool) -> str:
        self.decisions[key] = "APPROVED" if approved else "REJECTED"
        self.ledger.append("approval_decided", {"key": key, "approver": approver, "approved": approved})
        return self.decisions[key]
