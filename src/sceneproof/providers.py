"""Meta Model API adapters (Muse Spark / SAM 3.1 / Muse Image).

Contract: no key -> BLOCKED_CREDENTIALS, and the deterministic verifier still runs.
A model may *explain* or *segment*; it may never invent the verdict. Endpoints and
model ids are from https://dev.meta.ai/docs (Base URL https://api.meta.ai/v1,
Responses API, models muse-spark-1.3 / sam-3.1 / muse-image-1.0, auth: Bearer
$MODEL_API_KEY). Live calls are exercised only when a key is present.
"""
from __future__ import annotations
import json, os, urllib.request, urllib.error

BASE = os.environ.get("META_API_BASE", "https://api.meta.ai/v1")
SPARK = os.environ.get("META_MODEL", "muse-spark-1.3")
SAM = os.environ.get("META_SAM_MODEL", "sam-3.1")
IMAGE = os.environ.get("META_IMAGE_MODEL", "muse-image-1.0")

class BlockedCredentials(RuntimeError): pass

def _key() -> str:
    k = os.environ.get("MODEL_API_KEY", "").strip()
    if not k: raise BlockedCredentials("BLOCKED_CREDENTIALS: set MODEL_API_KEY to use Meta Model API")
    return k

def _post(path: str, payload: dict, timeout: int = 60) -> dict:
    req = urllib.request.Request(BASE + path, data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {_key()}", "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Meta Model API {e.code}: {e.read().decode()[:300]}") from e

def explain_verdict(report_dict: dict) -> tuple[str, str]:
    """Muse Spark explanation of a *deterministic* verdict. Offline fallback is
    labelled OFFLINE_REFERENCE so a demo never fakes a model call."""
    try:
        _key()
    except BlockedCredentials:
        v = report_dict["baseline"]
        lines = [f"Deterministic verdict: {'FEASIBLE' if v['feasible'] else 'INFEASIBLE'} "
                 f"(score {v['score']}/100) across {len(v['checks_run'])} constraint families."]
        for x in v["violations"]: lines.append(f"- [{x['rule']}] {x['detail']}")
        if report_dict.get("effect") is not None:
            lines.append(f"Counterfactual effect (intervened - baseline score): {report_dict['effect']:+.1f} points.")
        lines.append("Set MODEL_API_KEY to have Muse Spark narrate this same verdict — the verdict itself will not change.")
        return "\n".join(lines), "OFFLINE_REFERENCE"
    prompt = ("Explain this deterministic scene-verification verdict to a robotics engineer in "
              "under 120 words. Do not change, soften, or contradict any verdict, score, or "
              "violation. Verdict JSON:\n" + json.dumps(report_dict)[:6000])
    out = _post("/responses", {"model": SPARK, "input": prompt})
    text = out.get("output_text") or ""
    if not text:  # Responses API structured fallback
        for item in out.get("output", []):
            for c in item.get("content", []):
                if c.get("text"): text += c["text"]
    return (text or "(empty model response)"), f"META:{SPARK}"

def segment_scene(image_ref: str, prompt: str = "warehouse objects") -> dict:
    """SAM 3.1 segmentation via the Responses API. Gated: raises BlockedCredentials offline."""
    _key()
    return _post("/responses", {"model": SAM, "input": [
        {"role": "user", "content": [{"type": "input_text", "text": prompt},
                                     {"type": "input_image", "image_url": image_ref}]}]})

def render_counterfactual(prompt: str) -> dict:
    """Muse Image counterfactual render. Gated: raises BlockedCredentials offline."""
    _key()
    return _post("/images/generations", {"model": IMAGE, "prompt": prompt})
