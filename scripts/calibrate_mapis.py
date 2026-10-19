"""Hold threshold for MAPIS chosen on VALIDATION only, then applied to test (seed-variance fix for the multi-hop FPR).

MAPIS holds a message when its fused trust is < 0.50 (QUARANTINE). A session is held when its lowest trust is below the cut-off, so
one replay per session gives the result for any cut-off. This script replays validation and test once per model, picks the highest-recall
cut-off <= 0.50 whose validation FPR stays <= --max-fpr on EVERY dataset family with enough benign sessions, and reports test at the
default 0.50 and at the picked cut-off. The tier boundaries used inside the session (FLAG 0.75 raises sensitivity) are unchanged.

    python scripts/calibrate_mapis.py --model artifacts/mapis_detector --out results/calibration_seed42.json
    python scripts/calibrate_mapis.py --model artifacts/seed2/mapis_detector --out results/calibration_seed2.json
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import benchmark as B  # noqa: E402
from backend.config import Settings  # noqa: E402
from backend.core.shield import MapisShield  # noqa: E402
from backend.core.store import MemoryStore  # noqa: E402

SETS = "v1,decomposed,multihop,realharm,adaptive"


def lowest_trust(shield: MapisShield, samples: list[dict]) -> list[tuple[str, bool, float]]:
    out = []
    for s in samples:
        sid, low = uuid.uuid4().hex, 1.0
        for e in B.events(s):
            low = min(low, shield.inspect({"session_id": sid, **e}).trust)
        shield.reset(sid)
        out.append((s["source_dataset"], bool(s["is_attack"]), low))
    return out


def rates(rows, cut):
    a = [t for _, atk, t in rows if atk]
    b = [t for _, atk, t in rows if not atk]
    return {"cutoff": round(cut, 4), "recall": round(sum(t < cut for t in a) / max(1, len(a)), 4),
            "fpr": round(sum(t < cut for t in b) / max(1, len(b)), 4), "n_attacks": len(a), "n_benign": len(b)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="artifacts/mapis_detector")
    ap.add_argument("--sets", default=SETS)
    ap.add_argument("--max-fpr", type=float, default=0.02)
    ap.add_argument("--min-benign", type=int, default=20, help="families with fewer benign validation sessions do not constrain the cut-off")
    ap.add_argument("--out", default="results/calibration_mapis.json")
    args = ap.parse_args()
    shield = MapisShield(Settings(redis_url="", model_path=args.model), MemoryStore())
    sets = args.sets.split(",")
    val, test = lowest_trust(shield, B.load(sets, "validation")), lowest_trust(shield, B.load(sets, "test"))
    fams = sorted({r[0] for r in val})
    best = (rates(val, 0.5)["recall"] if all(rates([r for r in val if r[0] == f], 0.5)["fpr"] <= args.max_fpr for f in fams) else -1, 0.5)
    for cut in sorted({0.5, *[r[2] for r in val if r[2] < 0.5], *[r[2] + 1e-6 for r in val if r[2] < 0.5]}):
        if cut > 0.5:
            continue
        ok = all(rates(v, cut)["fpr"] <= args.max_fpr for f in fams if (v := [r for r in val if r[0] == f]) and rates(v, cut)["n_benign"] >= args.min_benign)
        rec = rates(val, cut)["recall"]
        if ok and (rec, cut) > best:
            best = (rec, cut)
    cut = best[1]
    report = {"model": args.model, "max_fpr_validation": args.max_fpr, "cutoff": round(cut, 4), "by_set": {}}
    for f in sorted({r[0] for r in test}):
        t = [r for r in test if r[0] == f]
        report["by_set"][f] = {"default_0.50": rates(t, 0.5), "calibrated": rates(t, cut), "validation_calibrated": rates([r for r in val if r[0] == f], cut)}
    report["overall"] = {"default_0.50": rates(test, 0.5), "calibrated": rates(test, cut)}
    print(f"cut-off picked on validation: {cut:.4f} (default 0.50)")
    for f, v in [*report["by_set"].items(), ("overall", report["overall"])]:
        d, c = v["default_0.50"], v["calibrated"]
        print(f"{f:22s} default: recall {d['recall']:.3f} FPR {d['fpr']:.3f} | calibrated: recall {c['recall']:.3f} FPR {c['fpr']:.3f}  (n={d['n_attacks']}+{d['n_benign']})")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
