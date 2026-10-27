"""Seeded synthetic scene generator + counterfactual interventions (clean-room)."""
from __future__ import annotations
import random
from .models import Scene, SceneObject, Intervention

def generate(seed: int = 7, scene_id: str = "demo-warehouse") -> Scene:
    """A grounded, feasible warehouse scene by construction."""
    objs = [
        SceneObject("shelf-1", "shelf", 0.05, 0.0, 0.28, 0.55),
        SceneObject("crate-a", "crate", 0.08, 0.55, 0.12, 0.12),
        SceneObject("crate-b", "crate", 0.40, 0.0, 0.14, 0.14),
        SceneObject("barrel-1", "barrel", 0.60, 0.0, 0.11, 0.22),
        SceneObject("cone-1", "cone", 0.78, 0.0, 0.06, 0.12),
        SceneObject("robot-1", "robot", 0.86, 0.0, 0.10, 0.18),
    ]
    if seed != 7:  # deterministic jitter that preserves groundedness
        rng = random.Random(seed)
        objs = [SceneObject(o.id, o.kind, round(min(0.9, max(0.0, o.x + rng.uniform(-0.02, 0.02))), 4),
                            o.y, o.w, o.h) for o in objs]
    return Scene(scene_id, tuple(objs), seed)

def apply(scene: Scene, iv: Intervention) -> Scene:
    objs = list(scene.objects)
    if iv.action == "remove":
        objs = [o for o in objs if o.id != iv.object_id]
    elif iv.action == "move":
        objs = [SceneObject(o.id, o.kind, round(o.x + iv.dx, 4), round(max(0.0, o.y + iv.dy), 4), o.w, o.h)
                if o.id == iv.object_id else o for o in objs]
    elif iv.action == "resize":
        objs = [SceneObject(o.id, o.kind, o.x, o.y, iv.w or o.w, iv.h or o.h)
                if o.id == iv.object_id else o for o in objs]
    elif iv.action == "add":
        objs.append(SceneObject(iv.object_id, iv.kind, round(0.5 + iv.dx, 4), round(max(0.0, iv.dy), 4),
                                iv.w or 0.1, iv.h or 0.1))
    else:
        raise ValueError(f"unknown intervention action: {iv.action}")
    return Scene(scene.id + ":cf", tuple(objs), scene.seed)
