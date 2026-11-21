"""Seeded synthetic scene generator + counterfactual interventions (clean-room)."""
from __future__ import annotations
import math
import random
from .models import KINDS, Scene, SceneObject, Intervention

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


def supplied_scene(value: object) -> Scene:
    """Read a bounded scene document; the verifier owns out-of-stage checks."""
    def identifier(v: object) -> bool:
        return (isinstance(v, str) and 1 <= len(v) <= 80 and v.strip() == v
                and v.isprintable())

    if not isinstance(value, dict) or not set(value) <= {"id", "seed", "objects"}:
        raise ValueError("Scene JSON must contain id, objects and an optional seed.")
    scene_id = value.get("id")
    seed = value.get("seed", 0)
    entries = value.get("objects")
    if not identifier(scene_id) or type(seed) is not int or not -(2**31) <= seed < 2**31:
        raise ValueError("Use a printable scene ID up to 80 characters and a 32-bit integer seed.")
    if not isinstance(entries, list) or not 1 <= len(entries) <= 64:
        raise ValueError("Supply between 1 and 64 scene objects.")
    objects = []
    seen = set()
    for index, item in enumerate(entries, 1):
        if not isinstance(item, dict) or set(item) != {"id", "kind", "x", "y", "w", "h"}:
            raise ValueError(f"Object {index} needs id, kind, x, y, w and h.")
        object_id, kind = item["id"], item["kind"]
        if not identifier(object_id) or object_id in seen:
            raise ValueError(f"Use a unique printable ID for object {index}.")
        if not isinstance(kind, str) or kind not in KINDS:
            raise ValueError(f"Object {index} has an unsupported kind.")
        coordinates = [item[key] for key in ("x", "y", "w", "h")]
        if any(type(v) not in (int, float) or not -2 <= v <= 2 or not math.isfinite(v)
               for v in coordinates) or not all(v > 0 for v in coordinates[2:]):
            raise ValueError(f"Object {index} needs bounded coordinates and positive dimensions.")
        seen.add(object_id)
        objects.append(SceneObject(object_id, kind, *(float(v) for v in coordinates)))
    return Scene(scene_id, tuple(objects), seed)
