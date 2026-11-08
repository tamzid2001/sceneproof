# Changelog

## 0.1.1 — 2026-11-08
- Interactive 2D scene editor: drag entities on the canvas, arrow-key nudging
  (keyboard path), form-equivalent move/resize/add/remove; pending
  counterfactuals rendered as ghosts explicitly labelled "pending · unverified".
- Before/after compare card now renders the server-verified `after_scene`
  returned by `POST /api/run` (previously the UI had no after-stage at all).
- Server-side request validation (`parse_intervention`): action whitelist,
  deltas within ±1, resize/add sizes within [0.01, 1], object-id charset,
  kind whitelist, no-op resize rejection, integer seed validation — honest 400
  messages (contract-tested over real HTTP, not mocked).
- Share links encode seed + counterfactual and replay the same verification.
- Hardened the UI: overlay toggle for constraint guides, reduced-motion and
  mobile layouts, focus-visible canvas styling.
- Tests: 16 → 39 (16 engine tests, 16 HTTP protocol tests, 7 Playwright E2E).
  Protocol and E2E suites run against a real server with a fresh engine each.
- No change to the verifier, ledger or provider contracts; all honesty labels
  (OFFLINE_REFERENCE / BLOCKED_CREDENTIALS / META:) preserved.

## 0.1.0 — 2026-10-27
- Initial hackathon release: deterministic scene verifier, counterfactual engine, human approval gate,
  hash-chained ledger, Muse Spark / SAM 3.1 / Muse Image adapters, bento web UI, CLI, 16 tests.
