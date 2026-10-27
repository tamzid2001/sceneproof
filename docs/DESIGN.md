# Design research → decisions

Researched 2026-10-27 against Dribbble and Mobbin. Sources are public search
surfaces; no paywalled Mobbin content was copied — patterns, not pixels.

## From Dribbble (trend-forward concepts)
- **Dark bento grids for AI products** — dense metric cards, radial glow, one
  accent colour. → SceneProof's bento home: stage (2fr) + score ring +
  violations + explanation + ledger, one accent (`#6d7cff`), red only for risk.
- **AI agent dashboards that prioritise readability over spectacle** (Groto-style
  analytical platforms). → 3–5 primary signals first (score, verdict, effect,
  chain validity), everything else behind progressive disclosure.

## From Mobbin (shipped-app flows, 600k+ screens)
- **Pre-flight intro before a consequential action** (Monzo/Qantas/N26 pattern:
  expectations, why, data handling before camera/permission). → "Before we
  verify your world" intro states exactly what the verifier does, what the
  models do, and the 4 steps — before any scene loads.
- **Progressive disclosure with step indicators** (Neo Financial 3-dot, DoorDash
  1-of-4). → 4-step stepper: Scene → Intervene → Verify → Report.
- **Empty states with context + guidance + visual** (Mobbin glossary). → the
  stage's empty state explains why it is empty and what loading a scene shows.
- **Permission/approval priming in real apps** → the approval gate appears only
  when an intervention is sensitive, names the approver, and explains that the
  decision is ledgered — mirroring Mobbin's approval-flow conventions.

## Anti-patterns deliberately avoided
- LLM-as-judge with no ground truth (the failure mode this product exists to fix).
- Fake "live model" output in offline demos. Offline is labelled, always.
- Dashboard maximalism: no card exists without a decision it supports.
