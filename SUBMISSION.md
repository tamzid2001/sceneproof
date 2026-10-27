# Hackathon submission — Meta Global AI Developer Hackathon 2026

- **Track:** Indie developer · **Theme:** 2 — Push the Frontier
- **Project:** SceneProof · **Repo:** https://github.com/tamzid2001/sceneproof
- **Live demo:** https://sceneproof-ten.vercel.app (public, no login, no keys needed)
- **Deadline:** Nov 4, 2026, 9:00 PM ET (judging Nov 4–8, winners Nov 9)

## One-liner
World models generate scenes that look right. SceneProof proves whether a
scene actually holds together — and what breaks when you change one thing —
with a deterministic verifier, a human approval gate, and a replayable proof.

## What it does
Load a robot's scene, apply a counterfactual ("remove the shelf", "move the
crate"), and get a verdict that is *computed, not opined*: bounds,
interpenetration, support/gravity and stack-stability checks, a feasibility
score, an effect size, and a hash-chained audit ledger a third party can
replay. Sensitive interventions require a named human's approval first.

## How Meta's models are used
- **Muse Spark 1.3** narrates the deterministic verdict (Responses API).
- **SAM 3.1** segments scene images into candidate objects (Responses API).
- **Muse Image** renders the counterfactual for visual comparison.
Models propose and explain; deterministic code decides. With no API key the
full demo still runs, honestly labelled `OFFLINE_REFERENCE` /
`BLOCKED_CREDENTIALS`.

## Judging map
- **Creativity:** "proof-carrying scenes" — unit tests for physical worlds;
  the approval-gated counterfactual is, to our knowledge, a new interaction.
- **Technical ambition:** constraint verification + hash-chained provenance +
  three Meta model surfaces behind one honest provider seam, zero runtime deps.
- **Functionality:** `pytest` green, CLI demo, live web UI, Docker, CI —
  runnable in under a minute with no keys and no paid services.

## Before you submit (checklist)
- [ ] Record the 2-minute demo (script: docs/DEMO_SCRIPT.md), upload unlisted.
- [ ] Paste the demo link + this file's text into the submission form.
- [ ] Optional: run once with a real `MODEL_API_KEY` and add the Muse Spark
      narration screenshot to the README.
- [ ] Confirm the form track = Indie, theme = Push the Frontier.
