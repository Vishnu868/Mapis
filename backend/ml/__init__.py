"""Phase 4 MAPIS transformer training infrastructure.

This package is deliberately separate from ``backend.core.trust_scorer``.
The latter remains the legacy heuristic baseline; this package defines the
untrained learned-model path whose trust score is 0=malicious and 1=safe.
"""

from .inference import TransformerTrustPredictor, TrustPrediction

__all__ = ["TransformerTrustPredictor", "TrustPrediction"]
