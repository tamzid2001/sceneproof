# Demo video script (target 2:00)

**0:00 — Hook.** "AI world models make scenes that look perfect. This crate is
floating. This robot's shelf is about to orphan everything on it. Looking right
is not being right. This is SceneProof."

**0:15 — Load.** Open the web UI. Read the pre-flight card: "Models explain,
code decides." Click *Load demo scene*. Point at the stage: six objects,
segmentation-style overlays, scene fingerprint.

**0:35 — Verify.** Click *Verify scene*. Score ring: 100, FEASIBLE, zero
violations. "Four constraint families: bounds, interpenetration, support,
stack stability. Deterministic — same scene, same proof, forever."

**0:55 — Counterfactual + approval gate.** Choose *crate-a → move Δy −0.55* is
boring; instead choose **Remove shelf-1**. The red approval gate appears:
"Sensitive interventions need a named human." Type your name, tick approve,
verify. Score collapses; `crate-a` is flagged **unsupported**; effect size shown.

**1:25 — Proof.** Open the ledger card: head hash, chain valid. Click *Export
report JSON*. "Anyone can replay this proof. The hash chain makes it
tamper-evident."

**1:40 — Meta models.** Show the Explanation card: offline runs say
`OFFLINE_REFERENCE` — "we never fake a model call." With `MODEL_API_KEY`,
Muse Spark narrates the same verdict, SAM 3.1 segments real images,
Muse Image renders the counterfactual. "The verdict never changes."

**1:55 — Close.** "SceneProof: segment it, intervene, prove it. Proof-carrying
scenes for the robots and world models we're about to trust."
