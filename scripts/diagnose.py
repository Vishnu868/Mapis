"""Show WHY sessions were held back (false positives) or missed (false negatives).

    python scripts/diagnose.py --sets v1 --kind benign            # which benign sessions were flagged, and by which signal
    python scripts/diagnose.py --sets bipia --kind attack --limit 15   # which attacks slipped through

For every offending session it prints each event that reached FLAG or worse (or, for a miss, the injected event) with the
classifier trust, the four stateful signals and the reasons, so thresholds / weights can be tuned on evidence.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from benchmark import build, events, load  # noqa: E402
from backend.core.shield import Tier  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", default="v1")
    ap.add_argument("--split", default="test")
    ap.add_argument("--kind", choices=["benign", "attack"], default="benign")
    ap.add_argument("--model", default="artifacts/mapis_detector")
    ap.add_argument("--limit", type=int, default=10)
    args = ap.parse_args()

    shield = build("mapis", args.model, "").shield
    shown = total = 0
    for s in load(args.sets.split(","), args.split):
        if s["is_attack"] != (args.kind == "attack"):
            continue
        sid, verdicts = uuid.uuid4().hex, []
        for e in events(s):
            verdicts.append(shield.inspect({"session_id": sid, **e}))
        shield.reset(sid)
        held = any(v.tier.severity >= Tier.QUARANTINE.severity for v in verdicts)
        offending = held if args.kind == "benign" else not held  # benign held = false positive; attack not held = miss
        total += 1
        if not offending:
            continue
        shown += 1
        if shown > args.limit:
            continue
        print(f"\n=== {'FALSE POSITIVE' if args.kind == 'benign' else 'MISSED ATTACK'}: {s['sample_id']} "
              f"({s['source_dataset']}, class={s.get('mapis_attack_class')}, kind={s.get('benign_kind')})")
        for v in verdicts:
            if args.kind == "benign" and v.tier is Tier.PASS:
                continue
            if args.kind == "attack" and v.role not in ("tool", "tool_response", "memory_read", "memory_write") and v.tier is Tier.PASS and v.model_trust is None:
                continue
            print(f"  hop {v.hop} {v.role:13s} {v.source}->{v.target} tier={v.tier.value:10s} trust={v.trust:.3f} model_trust={v.model_trust}")
            print(f"      signals={v.features}")
            print(f"      reasons={v.reasons}")
            print(f"      preview={v.preview[:140]!r}")
    print(f"\n{shown} of {total} {args.kind} sessions in {args.sets}/{args.split} were {'flagged' if args.kind == 'benign' else 'missed'}")


if __name__ == "__main__":
    main()
