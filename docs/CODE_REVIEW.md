# Deep code review — private portfolio → this public repo

Date: 2026-10-27. Scope: 98 GitHub repos under the author's account
(96 private, 2 public), with hands-on review of the 8 most recent private
repos plus the flagship local projects. **No private code was copied into
SceneProof** — it is a clean-room synthesis of patterns. Private repo names
below are the author's own.

## What was audited
- API-level inventory of all 98 repos (size, files, tests, licence, recency).
- Cloned and executed: `patch-correctness-verifier`,
  `visual-regression-evaluator`, `flashinfer-kv-cache-accountant`,
  `cosmos-counterfactual-scene-lab`, `agent-reliability-scorecard`,
  `agent-tool-permission-firewall`, `multiagent-workflow-engine`,
  `atmospheric-calibrated-forecast-platform`.
- Ran every test suite; scanned for secret patterns; measured cross-repo
  file duplication by content hash; checked web/UI assets.

## Findings
1. **Tests genuinely pass.** 104–572 tests per repo, all green except
   `atmospheric-calibrated-forecast-platform`, which fails collection when the
   optional `mcp` package is absent — an undeclared-dependency bug.
2. **Secret-scan hits were false positives** — the regexes inside the repos'
   own `security.yml` scanners, not credentials. No real secrets found.
3. **Heavy templating.** 24 cross-repo identical-file groups (shared security /
   recovery / acceptance tests, provider seams, RDMA benchmark stubs). Each repo
   is a competent *vertical slice*, and the READMEs honestly say so
   ("Wave 2 — not yet a full product", `BLOCKED_CREDENTIALS`, `LIMITATIONS.md`).
4. **Zero UI.** None of the 8 reviewed repos ships a single HTML/CSS/JS asset,
   despite several claiming a "web app" in prose (`src/web.py` is an API shim).
5. **Strengths worth keeping:** deterministic CPU-reference verifiers with golden
   fixtures; explicit execution states (never fake hardware/credentials);
   audit/provenance discipline; honest limitation docs; provider seams that let
   tests run offline.

## Verdict that shaped SceneProof
The portfolio proves one repeatable competence — **verification, scoring,
approval and audit of AI/system outputs** — across agents, patches, GPU kernels
and world models. It does not yet prove a *product*: no UI, no real model
integration, no single demo-able story. SceneProof therefore:

- keeps the proven core (deterministic verifier, approval gate, hash-chained
  ledger, honest blocked-states) and rebuilds it clean-room in ~600 LOC;
- adds the missing product layer (bento web UI, CLI, exportable proof report);
- adds the missing Meta layer (Muse Spark / SAM 3.1 / Muse Image adapters
  against the documented Meta Model API, gated on `MODEL_API_KEY`);
- picks the one domain where all of it composes and photographs well for
  judges: counterfactual scene verification for robotics/world models
  (Theme 2, *Push the Frontier*).
