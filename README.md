# SceneProof

**Segment it. Intervene. Prove it.**

**Live demo: https://sceneproof-ten.vercel.app** · Repo: https://github.com/tamzid2001/sceneproof

Counterfactual world-model verifier for robotics & embodied AI — built for the
**Meta Global AI Developer Hackathon 2026** (Oct 26 – Nov 4, 2026), Theme 2:
*Push the Frontier*, Indie track.

> World models and robot planners produce scenes that *look* right. SceneProof
> asks the harder question: **does this world actually hold together — and what
> breaks if we change one thing?** Every answer is a deterministic, replayable
> proof, not a model's opinion.

## The idea in 30 seconds

1. **Load a scene** — objects with geometry on a stage (or, with a key, segment a
   real image with **SAM 3.1**).
2. **Intervene** — move, remove, resize, add. *"What if the shelf disappears?"*
3. **Human approval gate** — sensitive interventions (removing a support, touching
   a human/vehicle) cannot run until a named human approves. The decision is
   written to a hash-chained audit ledger.
4. **Prove it** — a deterministic constraint engine (bounds, interpenetration,
   support/gravity, stack stability) re-verifies the counterfactual world and
   returns a signed-off verdict: feasible or not, score, violations, effect size.
5. **Explain it** — **Muse Spark 1.3** narrates the verdict. It may explain the
   proof; it may never change it. **Muse Image** can render the counterfactual.

That separation — *models propose and explain, deterministic code decides* — is
the product.

## Run it (no keys, no install friction)

```bash
python3 -m pytest -q                      # 16 tests, offline
PYTHONPATH=src python3 -m sceneproof demo # CLI proof in your terminal
PYTHONPATH=src python3 -m sceneproof.web --port 8000   # → http://127.0.0.1:8000
# or: pip install . && sceneproof demo
```

No `MODEL_API_KEY`? The demo still runs end-to-end and says so honestly:
explanations are labelled `OFFLINE_REFERENCE`, Meta calls report
`BLOCKED_CREDENTIALS`. Nothing is faked. With a key, set `MODEL_API_KEY`
(see `.env.example`) and the same verdicts get Muse Spark narration,
SAM 3.1 segmentation, and Muse Image counterfactual renders.

## How Meta models are used

| Model | Role in SceneProof | Endpoint |
|---|---|---|
| Muse Spark 1.3 (`muse-spark-1.3`) | Narrates deterministic verdicts for engineers | `POST /v1/responses` |
| SAM 3.1 (`sam-3.1`) | Segments a scene image into candidate objects | `POST /v1/responses` |
| Muse Image (`muse-image-1.0`) | Renders the counterfactual scene for visual diff | `POST /v1/images/generations` |

Base URL `https://api.meta.ai/v1`, Bearer `MODEL_API_KEY` — per
[Meta Model API docs](https://dev.meta.ai/docs). Adapters live in
`src/sceneproof/providers.py`; the verdict path never depends on them.

## Architecture

```
web UI (bento stage) ─┐
CLI ──────────────────┼─► Engine ─► Constraint verifier (source of truth)
                      │      ├────► Approval gate ─► hash-chained Ledger
                      │      └────► Meta adapters (explain / segment / render)
```

- `src/sceneproof/constraints.py` — the verifier. Deterministic, seeded, tested.
- `src/sceneproof/scene.py` — scene generator + counterfactual interventions.
- `src/sceneproof/ledger.py` — append-only hash chain; tamper-evident replay.
- `src/sceneproof/engine.py` — verify → approve → intervene → re-verify → explain.
- `src/sceneproof/web.py` + `web/` — zero-dependency UI (stdlib HTTP server) with
  server-validated interventions (`action`, bounded deltas/sizes, id/kind checks)
  and an `after_scene` counterfactual stage returned by `POST /api/run`.

Design language: Dribbble-style dark bento hierarchy for data density, Mobbin
shipped-app patterns (pre-flight intro, stepper, empty state, progressive
disclosure) for trust. Rationale in [docs/DESIGN.md](docs/DESIGN.md).

### Interactive editor (added 2026-11-08)

The stage is an interactive 2D editor of real scene entities:

- **Drag** any object directly on the canvas (pointer capture), or **nudge the
  selected object with arrow keys** — a keyboard-only path to the same
  counterfactual. The form (move/resize/add/remove) stays fully equivalent.
- A pending counterfactual is drawn as a dashed cyan ghost explicitly labelled
  **pending · unverified**. The UI only *proposes*: nothing counts until
  **Verify scene** posts it to the deterministic server.
- The **before/after compare** card is filled from the server's
  `after_scene` (the exact intervened stage the engine verified), never from UI
  geometry.
- **Share links** encode seed + pending counterfactual in the URL; opening one
  replays the *same* `POST /api/run` and shows the same verdict, honestly
  labelled (`OFFLINE_REFERENCE` without a key, `META:` with one).
- Sensitive interventions (remove, adding human/vehicle) still require a named
  human approval, written to the hash-chained ledger.
- Covered by **16 protocol tests** (`tests/test_web_api.py`) and **7 Playwright
  browser E2E tests** (`tests/test_e2e_playwright.py`) that drive the real UI in
  Chromium: load, drag, keyboard nudge, gated remove, gated add, share replay.

## Why this, why now

This repo is a clean-room synthesis of patterns proven across the author's
private research portfolio (agent reliability scorecards, permission firewalls,
human-approval ledgers, patch/world-model verifiers) — re-built from scratch as
one focused, public, demo-able product. The deep review that produced it is in
[docs/CODE_REVIEW.md](docs/CODE_REVIEW.md). What it deliberately does **not**
claim is in [LIMITATIONS.md](LIMITATIONS.md).

## Submission

Hackathon submission text, demo-video script and judging-criteria mapping:
[SUBMISSION.md](SUBMISSION.md) · [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md).
Submissions close **Nov 4, 2026, 9:00 PM ET**.

MIT — original work only. No private or third-party code copied.
