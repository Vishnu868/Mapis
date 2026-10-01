"""Content detectors. Both return a trust score (0 = malicious, 1 = safe)."""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from .features import instruction_risk


class RegexDetector:
    """Fallback used until a trained model exists. Deliberately weak: it only reads the current event."""

    name = "regex"
    use_context = False

    def score_chunks(self, texts: list[str], hop: dict) -> float:
        return 1.0 - 0.9 * instruction_risk(hop)[0]


class TransformerDetector:
    """DeBERTa-v3-small sequence classifier fine-tuned on MAPIS Phase-4 events."""

    name = "deberta-v3-small"

    def __init__(self, model_dir: str | Path):
        from backend.ml.inference import TrustPredictor

        self.predictor = TrustPredictor(model_dir)
        self.use_context = self.predictor.use_context

    def score_chunks(self, texts: list[str], hop: dict) -> float:
        """An event is as trustworthy as its least trustworthy chunk."""
        return min(self.predictor.trust(texts))


def load_detector(model_path: str | Path):
    if (Path(model_path) / "config.json").exists():
        detector = TransformerDetector(model_path)
        logger.info(f"Detector: {detector.name} from {model_path}")
        return detector
    logger.warning(f"No trained model at {model_path}; using the regex fallback detector")
    return RegexDetector()
