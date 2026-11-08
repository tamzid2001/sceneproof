# Changelog

## 0.1.2 — 2026-11-08 — approval-gate hardening (layered on 0.1.1)

Two real defects in the human-approval gate, both surfaced by new
contract tests (`tests/test_web_contract.py`, 15 tests over real HTTP):

1. **The gate could be bypassed by the client.** `Intervention.sensitive`
   decides sensitivity from `kind`, but the request parser built
   interventions with a client-supplied `kind` defaulting to `"crate"` —
   so moving or resizing a **human or vehicle** was never gated, exactly
   the case the documented rule promises to gate. `parse_intervention`
   now resolves the target's kind from the scene itself for
   move/remove/resize (and rejects unknown object ids with an honest
   400 instead of silently no-opping); `kind` is honoured only for
   `add`, where the object does not exist yet.
2. **Approvals were sticky for the life of the process.**
   `ApprovalGate.decisions` kept a key APPROVED forever, so after one
   human granted "remove shelf-1" every later request for the same key
   ran **unapproved** — a one-time grant had silently become a permanent
   bypass. Each sensitive run now requires its own attributable approval
   (named approver + decision in that request); earlier decisions remain
   in the hash-chained ledger as history.

`parse_intervention` now takes the scene as an argument; the CLI and
tests were adapted accordingly. 48 Python tests pass.

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
