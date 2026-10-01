"""Held-out evaluation of the trained detector on the Phase-4 test and test_ood splits (run once, after freezing).

    python -m backend.ml.evaluate --model artifacts/mapis_detector [--stateless artifacts/mapis_stateless]

Reports headline metrics, per-family recall, latency, and cheap baselines (role-only, length-only,
TF-IDF+logistic regression) on the same rows so the number can be defended, plus the stateless ablation.
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


def lexical_baselines(train, val, test) -> dict:
    """What cheap models score on the same rows: the bar a transformer must be compared against."""
    best = max(sorted({len(r["text"]) for r in val}), key=lambda t: summarize(confusion([r["label"] for r in val], [len(r["text"]) > t for r in val]))["f1"])
    out = {"role_only": role_only_baseline(train, test),
           "length_only": summarize(confusion([r["label"] for r in test], [len(r["text"]) > best for r in test]))}
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
    except ImportError:
        return out
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=50000, sublinear_tf=True)
    clf = LogisticRegression(max_iter=2000, class_weight="balanced").fit(vec.fit_transform([r["text"] for r in train]), [r["label"] for r in train])
    pred = clf.predict(vec.transform([r["text"] for r in test]))
    out["tfidf_logreg"] = summarize(confusion([r["label"] for r in test], [p == 0 for p in pred]))
    return out


def evaluate(model_dir: str, data: str, stateless_dir: str | None = None, threshold: float = 0.5) -> dict:
    """Headline = test (unseen sessions) and test_ood (attack templates never seen in training). <INFORMATION> tags are stripped."""
    from backend.ml.inference import TrustPredictor

    predictor = TrustPredictor(model_dir)
    train, val = (load_rows(data, s, predictor.use_context) for s in ("train", "validation"))
    result = {"device": str(predictor.device), "threshold": threshold, "splits": {}}
    for split in ("test", "test_ood"):
        test = load_rows(data, split, predictor.use_context)
        labels = [r["label"] for r in test]
        t0 = time.perf_counter()
        trust = predictor.trust([r["text"] for r in test])
        batched_ms = 1000 * (time.perf_counter() - t0) / len(test)
        report = {"examples": len(test), "headline": at_threshold(labels, trust, threshold), "per_attack_family_recall": {}, "per_source": {},
                  "baselines_same_rows": lexical_baselines(train, val, test)}
        by_family = defaultdict(list)
        for r, t in zip(test, trust):
            if r["label"] == 0:
                by_family[r["attack_family"]].append(t < threshold)
        report["per_attack_family_recall"] = {str(f): {"n": len(v), "recall": round(sum(v) / len(v), 4)} for f, v in sorted(by_family.items(), key=lambda kv: str(kv[0]))}
        for src in sorted({r["source"] for r in test}):
            idx = [i for i, r in enumerate(test) if r["source"] == src]
            report["per_source"][src] = at_threshold([labels[i] for i in idx], [trust[i] for i in idx], threshold)
        if split == "test":
            sample = [r["text"] for r in test[:50]]
            t0 = time.perf_counter()
            for text in sample:
                predictor.trust([text])
            report["latency_ms"] = {"per_event_single": round(1000 * (time.perf_counter() - t0) / len(sample), 1), "per_event_batched": round(batched_ms, 1)}
        if stateless_dir:
            sl = TrustPredictor(stateless_dir)
            sl_rows = load_rows(data, split, sl.use_context)
            report["ablation_stateless"] = at_threshold([r["label"] for r in sl_rows], sl.trust([r["text"] for r in sl_rows]), threshold)
        result["splits"][split] = report
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="artifacts/mapis_detector")
    ap.add_argument("--data", default="data/training/mapis_phase4_events_v2.jsonl")
    ap.add_argument("--stateless")
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--out", default="results/phase4_test_metrics.json")
    args = ap.parse_args()
    res = evaluate(args.model, args.data, args.stateless, args.threshold)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(res, indent=2) + "\n")
    print(json.dumps(res, indent=2))
