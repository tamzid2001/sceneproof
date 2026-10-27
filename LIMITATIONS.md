# Limitations (honest, by design)

- 2D side-view stage geometry; no 3D physics, friction, or dynamics simulation.
- The verifier checks the four constraint families in `constraints.py` — it is a
  feasibility gate, not a physics engine, and not a safety certification.
- Live Meta Model API calls require the author's own `MODEL_API_KEY`; they were
  not exercised in CI. Offline output is always labelled `OFFLINE_REFERENCE`.
- SAM 3.1 / Muse Image adapters implement the documented endpoints but their
  live response parsing should be re-checked against the API at demo time.
- Synthetic scenes only in the demo path; no real robot, dataset, or hardware
  was used or is claimed.
