"""Trust predictor: P(SAFE) from the fine-tuned encoder, temperature-calibrated."""

from __future__ import annotations

import json
from pathlib import Path


class TrustPredictor:
    def __init__(self, model_dir: str | Path, device: str | None = None):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self.torch = torch
        model_dir = Path(model_dir)
        meta = json.loads((model_dir / "calibration.json").read_text()) if (model_dir / "calibration.json").exists() else {}
        self.temperature = float(meta.get("temperature", 1.0))
        self.max_length = int(meta.get("max_length", 384))
        self.use_context = bool(meta.get("use_context", True))
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_dir).to(self.device).eval()

    def logits(self, texts: list[str], batch_size: int = 16):
        out = []
        order = sorted(range(len(texts)), key=lambda i: len(texts[i]))  # similar lengths -> less padding
        with self.torch.inference_mode():
            for start in range(0, len(order), batch_size):
                idx = order[start:start + batch_size]
                enc = self.tokenizer([texts[i] for i in idx], padding=True, truncation=True,
                                     max_length=self.max_length, return_tensors="pt").to(self.device)
                out.extend(zip(idx, self.model(**enc).logits.float().cpu()))
        return self.torch.stack([l for _, l in sorted(out, key=lambda p: p[0])]) if out else self.torch.empty(0, 2)

    def trust(self, texts: list[str], batch_size: int = 16) -> list[float]:
        return self.torch.softmax(self.logits(texts, batch_size) / self.temperature, dim=-1)[:, 1].tolist()
