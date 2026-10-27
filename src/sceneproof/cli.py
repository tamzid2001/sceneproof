"""CLI: python -m sceneproof demo | verify --seed 7 | counterfactual ..."""
from __future__ import annotations
import argparse, json, sys
from .engine import Engine
from .ledger import ApprovalRequired
from .models import Intervention
from .scene import generate

def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="sceneproof")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("demo", "verify"):
        s = sub.add_parser(name); s.add_argument("--seed", type=int, default=7)
    c = sub.add_parser("counterfactual")
    c.add_argument("--seed", type=int, default=7); c.add_argument("--action", default="move")
    c.add_argument("--object", default="crate-b"); c.add_argument("--dx", type=float, default=0.0)
    c.add_argument("--dy", type=float, default=0.0); c.add_argument("--approve", action="store_true")
    c.add_argument("--approver", default="cli-operator")
    a = p.parse_args(argv)
    eng, scene = Engine(), generate(a.seed)
    try:
        if a.cmd in ("demo", "verify"):
            rep = eng.run(scene)
        else:
            iv = Intervention(a.action, a.object, dx=a.dx, dy=a.dy)
            rep = eng.run(scene, iv, approver=a.approver if a.approve else None, approved=a.approve)
    except ApprovalRequired as e:
        print(json.dumps({"status": "APPROVAL_REQUIRED", "detail": str(e)}), file=sys.stderr); return 3
    print(json.dumps(rep.to_dict(), indent=2))
    print(f"\nledger_head={rep.ledger_head} chain_valid={eng.ledger.verify_chain()} source={rep.explanation_source}")
    print(rep.explanation)
    return 0 if rep.baseline.feasible else 1

if __name__ == "__main__":
    raise SystemExit(main())
