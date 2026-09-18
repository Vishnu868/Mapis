"""Probability and trust-score utilities for the new Phase 4 contract."""

from typing import Sequence


MALICIOUS_LABEL = 0
SAFE_LABEL = 1


def safe_trust_score(probabilities: Sequence[float]) -> float:
    """Return P(safe), where 0 means malicious and 1 means safe.

    Classifier labels are fixed as 0=MALICIOUS and 1=SAFE.  This function is
    intentionally independent of the legacy heuristic's reversed score.
    """
    if len(probabilities) != 2:
        raise ValueError("Expected probabilities ordered as [malicious, safe]")
    score = float(probabilities[SAFE_LABEL])
    if not 0.0 <= score <= 1.0:
        raise ValueError("Probabilities must be in [0, 1]")
    return score


def predicted_label(probabilities: Sequence[float]) -> str:
    return "SAFE" if safe_trust_score(probabilities) >= 0.5 else "MALICIOUS"
