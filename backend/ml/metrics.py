"""Detection metrics. 'Positive' means malicious (label 0), as in the First Review slides."""

from __future__ import annotations

import math
from collections.abc import Sequence


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a proportion (honest with small n, unlike the normal approximation)."""
    if n == 0:
        return 0.0, 1.0
    p, d = k / n, 1 + z * z / n
    centre, half = (p + z * z / (2 * n)) / d, z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round(max(0.0, centre - half), 4), round(min(1.0, centre + half), 4)


def confusion(labels: Sequence[int], flagged: Sequence[bool]) -> dict[str, int]:
    """labels: 0 = malicious, 1 = safe.  flagged: the system raised an alarm."""
    tp = sum(1 for y, f in zip(labels, flagged) if y == 0 and f)
    fn = sum(1 for y, f in zip(labels, flagged) if y == 0 and not f)
    fp = sum(1 for y, f in zip(labels, flagged) if y == 1 and f)
    tn = sum(1 for y, f in zip(labels, flagged) if y == 1 and not f)
    return {"tp": tp, "fn": fn, "fp": fp, "tn": tn}


def summarize(c: dict[str, int]) -> dict[str, float]:
    tp, fn, fp, tn = c["tp"], c["fn"], c["fp"], c["tn"]
    div = lambda a, b: a / b if b else 0.0  # noqa: E731
    precision, recall = div(tp, tp + fp), div(tp, tp + fn)
    return {**c, "n": tp + fn + fp + tn, "accuracy": div(tp + tn, tp + fn + fp + tn), "precision": precision,
            "recall": recall, "f1": div(2 * precision * recall, precision + recall), "fpr": div(fp, fp + tn),
            "recall_ci95": wilson(tp, tp + fn), "fpr_ci95": wilson(fp, fp + tn)}


def at_threshold(labels: Sequence[int], trust: Sequence[float], threshold: float) -> dict[str, float]:
    return summarize(confusion(labels, [t < threshold for t in trust]))


def best_threshold(labels: Sequence[int], trust: Sequence[float], max_fpr: float = 0.05) -> float:
    """Highest-F1 trust threshold whose FPR stays within max_fpr (tuned on validation only)."""
    best, best_f1 = 0.5, -1.0
    for t in sorted(set(trust)) + [1.0]:
        m = at_threshold(labels, trust, t)
        if m["fpr"] <= max_fpr and m["f1"] > best_f1:
            best, best_f1 = t, m["f1"]
    return best
