"""Inference interface for a trained Phase 4 Transformer artifact."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .calibration import predicted_label, safe_trust_score


@dataclass(frozen=True)
class TrustPrediction:
    malicious_probability: float
    safe_trust_score: float
    predicted_label: str


class TransformerTrustPredictor:
    """Lazy predictor; model files are required only when used, not imported."""

    def __init__(self, model_path: str | Path, max_length: int = 384):
        self.model_path = str(model_path)
        self.max_length = max_length
        self._model = None
        self._tokenizer = None

    def _load(self) -> None:
        if self._model is not None:
            return
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        import torch

        self._tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        self._model = AutoModelForSequenceClassification.from_pretrained(self.model_path)
        self._model.eval()
        self._torch = torch

    def predict(self, text: str) -> TrustPrediction:
        self._load()
        encoded = self._tokenizer(text, return_tensors="pt", truncation=True, max_length=self.max_length)
        with self._torch.no_grad():
            logits = self._model(**encoded).logits[0]
            probabilities = self._torch.softmax(logits, dim=-1).tolist()
        trust = safe_trust_score(probabilities)
        return TrustPrediction(
            malicious_probability=float(probabilities[0]),
            safe_trust_score=trust,
            predicted_label=predicted_label(probabilities),
        )
