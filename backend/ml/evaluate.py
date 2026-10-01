"""Held-out evaluation of the trained detector on the Phase-4 TEST split (run once, after freezing).

    python -m backend.ml.evaluate --model artifacts/mapis_detector [--stateless artifacts/mapis_stateless]

Reports headline metrics, per-class recall, latency, and three shortcut diagnostics
so the number can be defended: a role-only baseline, a marker-stripped re-score, and
(optionally) the stateless ablation.
"""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter, defaultdict
from pathlib import Path

from .data import MARKERS, load_rows
from .metrics import at_threshold, summarize, confusion


def role_only_baseline(train_rows, test_rows):
    """Predict by the majority training label of (source dataset, role). If this scores well, labels leak through role."""
    votes = defaultdict(Counter)
    for r in train_rows:
        votes[(r["source"], r["role"])][r["label"]] += 1
    pred = lambda r: votes[(r["source"], r["role"])].most_common(1)[0][0] if votes[(r["source"], r["role"])] else 1  # noqa: E731
    return summarize(confusion([r["label"] for r in test_rows], [pred(r) == 0 for r in test_rows]))


def evaluate(model_dir: str, data: str, stateless_dir: str | None = None, threshold: float = 0.5) -> dict:
    from backend.ml.inference import TrustPredictor

    predictor = TrustPredictor(model_dir)
    test = load_rows(data, "test", predictor.use_context)
    labels = [r["label"] for r in test]

    t0 = time.perf_counter()
    trust = predictor.trust([r["text"] for r in test])
    batched_ms = 1000 * (time.perf_counter() - t0) / len(test)
    sample = [r["text"] for r in test[:50]]
    t0 = time.perf_counter()
    for text in sample:
        predictor.trust([text])
    single_ms = 1000 * (time.perf_counter() - t0) / max(len(sample), 1)

    result = {"examples": len(test), "device": str(predictor.device), "threshold": threshold,
              "headline": at_threshold(labels, trust, threshold),
              "latency_ms": {"per_event_single": round(single_ms, 1), "per_event_batched": round(batched_ms, 1)},
              "per_attack_class_recall": {}, "per_source": {}}

    by_class = defaultdict(list)
    for r, t in zip(test, trust):
        if r["label"] == 0:
            by_class[r["attack_class"]].append(t < threshold)
    result["per_attack_class_recall"] = {c: {"n": len(v), "recall": round(sum(v) / len(v), 4)} for c, v in sorted(by_class.items(), key=lambda kv: str(kv[0]))}
    for src in sorted({r["source"] for r in test}):
        idx = [i for i, r in enumerate(test) if r["source"] == src]
        result["per_source"][src] = at_threshold([labels[i] for i in idx], [trust[i] for i in idx], threshold)

    train = load_rows(data, "train", predictor.use_context)
    result["diagnostic_role_only_baseline"] = role_only_baseline(train, test)
    stripped = predictor.trust([MARKERS.sub("", r["text"]) for r in test])
    result["diagnostic_markers_stripped"] = at_threshold(labels, stripped, threshold)

    if stateless_dir:
        sl = TrustPredictor(stateless_dir)
        sl_test = load_rows(data, "test", sl.use_context)
        result["ablation_stateless"] = at_threshold([r["label"] for r in sl_test], sl.trust([r["text"] for r in sl_test]), threshold)
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="artifacts/mapis_detector")
    ap.add_argument("--data", default="data/training/mapis_phase4_events_v1.jsonl")
    ap.add_argument("--stateless")
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--out", default="results/phase4_test_metrics.json")
    args = ap.parse_args()
    res = evaluate(args.model, args.data, args.stateless, args.threshold)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(res, indent=2) + "\n")
    print(json.dumps(res, indent=2))
