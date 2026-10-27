"""Deterministic physics/constraint verifier. This is the product's source of truth:
an LLM may explain a verdict, it may never create one."""
from __future__ import annotations
from .models import Scene, Verdict, Violation

EPS = 0.011

def _bounds(s: Scene):
    return [Violation("out_of_bounds", (o.id,), 1.0, f"{o.id} leaves the [0,1]x[0,1] stage")
            for o in s.objects if o.x < -1e-9 or o.y < -1e-9 or o.right > 1 + 1e-9 or o.top > 1 + 1e-9]

def _interpenetration(s: Scene):
    out = []
    for i, a in enumerate(s.objects):
        for b in s.objects[i + 1:]:
            area = a.overlap_area(b)
            if area > 0.0005:
                out.append(Violation("interpenetration", (a.id, b.id), min(1.0, area * 40),
                                     f"{a.id} and {b.id} occupy the same volume (overlap {area:.4f})"))
    return out

def _supporters(s: Scene, o):
    return [p for p in s.objects if p.id != o.id and abs(o.y - p.top) <= EPS and o.x_overlap(p) > 0]

def _support(s: Scene):
    out = []
    for o in s.objects:
        if o.y <= EPS: continue
        sup = _supporters(s, o)
        if not sup:
            out.append(Violation("unsupported", (o.id,), min(1.0, o.y * 2),
                                 f"{o.id} floats at height {o.y:.2f} with nothing beneath it"))
        elif not any(p.x - 1e-9 <= o.cx <= p.right + 1e-9 for p in sup):
            out.append(Violation("unstable_stack", (o.id,) + tuple(p.id for p in sup), 0.7,
                                 f"{o.id} centre of mass falls outside its support"))
    return out

def _orphaned(s: Scene):
    """Objects whose only supporter was removed are caught by _support; this flags
    tall stacks (>3) as a stability risk worth a human look."""
    out = []
    for o in s.objects:
        depth, cur = 0, o
        seen = set()
        while cur.y > EPS and cur.id not in seen:
            seen.add(cur.id)
            sup = _supporters(s, cur)
            if not sup: break
            cur, depth = sup[0], depth + 1
            if depth > 3:
                out.append(Violation("tall_stack", (o.id,), 0.4, f"{o.id} sits on a stack of depth {depth}"))
                break
    return out

CHECKS = {"out_of_bounds": _bounds, "interpenetration": _interpenetration,
          "unsupported": _support, "stack_stability": _orphaned}

def verify(scene: Scene) -> Verdict:
    violations: list[Violation] = []
    for fn in CHECKS.values(): violations.extend(fn(scene))
    penalty = sum(v.severity for v in violations)
    score = max(0.0, 100.0 - 34.0 * penalty)
    hard = any(v.rule in {"out_of_bounds", "interpenetration", "unsupported"} and v.severity >= 0.2 for v in violations)
    return Verdict(scene.id, not hard, score, tuple(violations), tuple(CHECKS))
