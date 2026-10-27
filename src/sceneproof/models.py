"""Domain models. Coordinates: x in [0,1] left->right, y in [0,1] bottom->top (0 = ground)."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
import hashlib, json

KINDS = {"crate", "robot", "human", "barrel", "cone", "vehicle", "shelf"}

@dataclass(frozen=True)
class SceneObject:
    id: str
    kind: str
    x: float  # left edge
    y: float  # bottom edge, 0 = ground
    w: float
    h: float
    @property
    def right(self): return self.x + self.w
    @property
    def top(self): return self.y + self.h
    @property
    def cx(self): return self.x + self.w / 2
    def overlap_area(self, o: "SceneObject") -> float:
        dx = max(0.0, min(self.right, o.right) - max(self.x, o.x))
        dy = max(0.0, min(self.top, o.top) - max(self.y, o.y))
        return dx * dy
    def x_overlap(self, o: "SceneObject") -> float:
        return max(0.0, min(self.right, o.right) - max(self.x, o.x))

@dataclass(frozen=True)
class Scene:
    id: str
    objects: tuple[SceneObject, ...]
    seed: int = 0
    def get(self, oid: str) -> SceneObject:
        for o in self.objects:
            if o.id == oid: return o
        raise KeyError(oid)
    def to_dict(self): return {"id": self.id, "seed": self.seed, "objects": [asdict(o) for o in self.objects]}
    @staticmethod
    def from_dict(d: dict) -> "Scene":
        return Scene(d["id"], tuple(SceneObject(**o) for o in d["objects"]), int(d.get("seed", 0)))
    def fingerprint(self) -> str:
        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True).encode()).hexdigest()[:16]

@dataclass(frozen=True)
class Violation:
    rule: str
    objects: tuple[str, ...]
    severity: float  # 0..1
    detail: str

@dataclass(frozen=True)
class Verdict:
    scene_id: str
    feasible: bool
    score: float  # 0..100
    violations: tuple[Violation, ...]
    checks_run: tuple[str, ...]
    def to_dict(self):
        return {"scene_id": self.scene_id, "feasible": self.feasible, "score": round(self.score, 2),
                "checks_run": list(self.checks_run),
                "violations": [{"rule": v.rule, "objects": list(v.objects), "severity": round(v.severity, 3), "detail": v.detail} for v in self.violations]}

@dataclass(frozen=True)
class Intervention:
    action: str  # move | remove | add | resize
    object_id: str
    dx: float = 0.0
    dy: float = 0.0
    w: float = 0.0
    h: float = 0.0
    kind: str = "crate"
    @property
    def sensitive(self) -> bool:
        """Removing a support or moving a human/vehicle needs human approval."""
        return self.action == "remove" or self.kind in {"human", "vehicle"}

@dataclass
class Report:
    baseline: Verdict
    intervened: Verdict | None = None
    effect: float | None = None
    explanation: str = ""
    explanation_source: str = "OFFLINE_REFERENCE"  # never relabelled as a model call
    ledger_head: str = ""
    approvals: list = field(default_factory=list)
    def to_dict(self):
        return {"baseline": self.baseline.to_dict(),
                "intervened": self.intervened.to_dict() if self.intervened else None,
                "effect": None if self.effect is None else round(self.effect, 2),
                "explanation": self.explanation, "explanation_source": self.explanation_source,
                "ledger_head": self.ledger_head, "approvals": self.approvals}
