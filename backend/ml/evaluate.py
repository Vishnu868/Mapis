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

from .data import load_events, load_rows
from .metrics import at_threshold, confusion, summarize


def role_only_baseline(train_rows, events):
    """Predict by the majority training label of (source dataset, role). If this scores well, labels leak through role."""
    votes = defaultdict(Counter)
    for r in train_rows:
        votes[(r["source"], r["role"])][r["label"]] += 1
    pred = lambda e: votes[(e["source"], e["role"])].most_common(1)[0][0] if votes[(e["source"], e["role"])] else 1  # noqa: E731
    return summarize(confusion([e["label"] for e in events], [pred(e) == 0 for e in events]))


def lexical_baselines(train, val, events) -> dict:
    """What cheap models score on the same events: the bar a transformer must be compared against."""
    labels = [e["label"] for e in events]
    best = max(sorted({len(r["text"]) for r in val}), key=lambda t: summarize(confusion([r["label"] for r in val], [len(r["text"]) > t for r in val]))["f1"])
    out = {"role_only": role_only_baseline(train, events),
           "length_only": summarize(confusion(labels, [any(len(t) > best for t in e["texts"]) for e in events]))}
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
    except ImportError:
        return out
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=50000, sublinear_tf=True)
    clf = LogisticRegression(max_iter=2000, class_weight="balanced").fit(vec.fit_transform([r["text"] for r in train]), [r["label"] for r in train])
    out["tfidf_logreg"] = summarize(confusion(labels, [any(p == 0 for p in clf.predict(vec.transform(e["texts"]))) for e in events]))
    return out


def event_trust(predictor, events) -> list[float]:
    """Trust of an event = min over its chunks (one batched pass over all chunks)."""
    flat = [t for e in events for t in e["texts"]]
    trust, out, i = predictor.trust(flat), [], 0
    for e in events:
        out.append(min(trust[i:i + len(e["texts"])]))
        i += len(e["texts"])
    return out


SPLITS = ("test", "test_ood", "test_bipia", "test_multihop", "test_realharm", "test_adaptive")  # unseen sessions | unseen attack templates | unseen dataset (BIPIA test)


def evaluate(model_dir: str, data: str, stateless_dir: str | None = None, threshold: float = 0.5) -> dict:
    """Event-level metrics on three held-out splits. Tags are stripped; long events are scored chunk-wise (min)."""
    from backend.ml.inference import TrustPredictor

    predictor = TrustPredictor(model_dir)
    train, val = (load_rows(data, s, predictor.use_context) for s in ("train", "validation"))
    result = {"device": str(predictor.device), "threshold": threshold, "splits": {}}
    for split in SPLITS:
        events = load_events(data, split, predictor.use_context)
        if not events:
            continue
        labels = [e["label"] for e in events]
        t0 = time.perf_counter()
        trust = event_trust(predictor, events)
        batched_ms = 1000 * (time.perf_counter() - t0) / len(events)
        report = {"events": len(events), "headline": at_threshold(labels, trust, threshold), "per_attack_family_recall": {}, "per_source": {},
                  "baselines_same_events": lexical_baselines(train, val, events)}
        by_family = defaultdict(list)
        for e, t in zip(events, trust):
            if e["label"] == 0:
                by_family[e["attack_family"]].append(t < threshold)
        report["per_attack_family_recall"] = {str(f): {"n": len(v), "recall": round(sum(v) / len(v), 4)} for f, v in sorted(by_family.items(), key=lambda kv: str(kv[0]))}
        for src in sorted({e["source"] for e in events}):
            idx = [i for i, e in enumerate(events) if e["source"] == src]
            report["per_source"][src] = at_threshold([labels[i] for i in idx], [trust[i] for i in idx], threshold)
        if split == "test":
            sample = events[:40]
            t0 = time.perf_counter()
            for e in sample:
                predictor.trust(e["texts"])
            report["latency_ms"] = {"per_event_single": round(1000 * (time.perf_counter() - t0) / len(sample), 1), "per_event_batched": round(batched_ms, 1)}
        if stateless_dir:
            sl = TrustPredictor(stateless_dir)
            sl_events = load_events(data, split, sl.use_context)
            report["ablation_stateless"] = at_threshold([e["label"] for e in sl_events], event_trust(sl, sl_events), threshold)
        result["splits"][split] = report
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="artifacts/mapis_detector")
    ap.add_argument("--data", default="data/training/mapis_phase4_events_v4.jsonl")
    ap.add_argument("--stateless")
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--out", default="results/phase4_test_metrics.json")
    args = ap.parse_args()
    res = evaluate(args.model, args.data, args.stateless, args.threshold)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(res, indent=2) + "\n")
    print(json.dumps(res, indent=2))
