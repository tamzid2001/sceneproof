# Architecture

Engine flow: verify -> approval gate (sensitive only) -> apply counterfactual -> re-verify -> explain -> ledger.
The constraint verifier (`constraints.py`) is the only source of verdict truth; Meta adapters (`providers.py`)
are behind an env-gated seam and can explain/segment/render but never decide. The ledger (`ledger.py`) is an
append-only SHA-256 hash chain; `verify_chain()` detects tampering. Web layer is stdlib-only so the demo runs
anywhere Python 3.10+ runs, with no build step.
