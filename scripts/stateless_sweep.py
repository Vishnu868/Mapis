"""Fair stateless comparison: the stateless DeBERTa at a threshold that gives <= 5 % FPR (chosen on the VALIDATION split, applied to test).

The default threshold (0.5) lets a stateless model reach high recall on multi-hop sessions only by also flagging most benign twins
(FPR 40-50 %): it cannot tell an attack from the same action the user asked for. This script answers "what recall can a stateless
model reach if it is held to the same false-positive budget as MAPIS?".

    python scripts/stateless_sweep.py --sets multihop,adaptive,realharm --out results/stateless_sweep.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import benchmark as B  # noqa: E402
from backend.core.context import build_texts, normalize_hop  # noqa: E402
from backend.core.detector import load_detector  # noqa: E402


def min_trusts(detector, samples: list[dict]) -> list[tuple[str, bool, float]]:
    out = []
    for s in samples:
        lowest = 1.0
        for i, e in enumerate(B.events(s), 1):
            if e["role"] in ("user", "system"):
                continue
            hop = normalize_hop({**e, "hop": i})
            lowest = min(lowest, detector.score_chunks(build_texts([], hop), hop)[0])
        out.append((s["source_dataset"], bool(s["is_attack"]), lowest))
    return out


def rates(rows: list[tuple[str, bool, float]], threshold: float) -> dict:
    a = [t for _, atk, t in rows if atk]
    b = [t for _, atk, t in rows if not atk]
    return {"threshold": round(threshold, 5), "recall": round(sum(t < threshold for t in a) / max(1, len(a)), 4),
            "fpr": round(sum(t < threshold for t in b) / max(1, len(b)), 4), "n_attacks": len(a), "n_benign": len(b)}


def pick_threshold(rows: list[tuple[str, bool, float]], max_fpr: float) -> float:
    """Highest-recall threshold whose FPR on `rows` is <= max_fpr (held = min trust < threshold)."""
    best = (-1.0, 0.0)
    for t in sorted({0.0, 0.5, *[r[2] for r in rows]}):
        for cand in (t, t + 1e-9):
            r = rates(rows, cand)
            if r["fpr"] <= max_fpr and (r["recall"], -r["fpr"]) > (best[0], 0.0) and cand <= 0.5 + 1e-9:
                best = (r["recall"], cand)
    return best[1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", default="multihop,adaptive,realharm")
    ap.add_argument("--stateless-model", default="artifacts/mapis_stateless")
    ap.add_argument("--max-fpr", type=float, default=0.05)
    ap.add_argument("--out", default="results/stateless_sweep.json")
    args = ap.parse_args()
    detector = load_detector(args.stateless_model)
    sets = args.sets.split(",")
    val = min_trusts(detector, B.load(sets, "validation"))
    test = min_trusts(detector, B.load(sets, "test"))
    report = {"max_fpr": args.max_fpr, "validation_sessions": len(val), "test_sessions": len(test), "by_set": {}}
    # one threshold per dataset family (each is a different attack surface), chosen on validation only
    for name in sorted({r[0] for r in test}):
        v, t = [r for r in val if r[0] == name], [r for r in test if r[0] == name]
        th = pick_threshold(v, args.max_fpr) if v else 0.5
        report["by_set"][name] = {"default_0.5": rates(t, 0.5), "val_matched_fpr": rates(t, th),
                                  "oracle_curve_on_test": [rates(t, x) for x in (0.5, 0.25, 0.1, 0.05, 0.01, 0.001)]}
        d, m = report["by_set"][name]["default_0.5"], report["by_set"][name]["val_matched_fpr"]
        print(f"{name:20s} default 0.5: recall {d['recall']:.3f} FPR {d['fpr']:.3f} | threshold {m['threshold']:.4f} (FPR<={args.max_fpr} on validation): "
              f"recall {m['recall']:.3f} FPR {m['fpr']:.3f}  (attacks {m['n_attacks']}, benign {m['n_benign']})")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
