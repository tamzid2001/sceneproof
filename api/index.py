"""Vercel serverless entrypoint: reuses the stdlib HTTP handler from sceneproof.web."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sceneproof.web import H  # noqa: E402

class handler(H):  # noqa: N801 — Vercel requires a top-level `handler`
    pass
