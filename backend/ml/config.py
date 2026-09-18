"""Reproducible, RTX-3050-conscious configuration for Phase 4 training."""

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import json


@dataclass(frozen=True)
class TrainingConfig:
    """Defaults are conservative for an 8 GB-class RTX 3050.

    LoRA is intentionally not enabled here: the base model is small enough for
    a first full fine-tuning run with gradient accumulation.  It can be added
    later only if measured GPU memory requires it.
    """

    model_name: str = "microsoft/deberta-v3-small"
    max_length: int = 384
    train_batch_size: int = 4
    eval_batch_size: int = 8
    gradient_accumulation_steps: int = 4
    learning_rate: float = 2e-5
    epochs: int = 3
    weight_decay: float = 0.01
    warmup_ratio: float = 0.1
    seed: int = 42
    use_mixed_precision: bool = True
    output_dir: str = "artifacts/phase4_transformer"
    training_data: str = "data/training/mapis_phase4_events_v1.jsonl"
    checkpoint_every_epoch: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")
