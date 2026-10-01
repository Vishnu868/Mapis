"""Training configuration (defaults sized for an 8 GB RTX 3050)."""

from dataclasses import asdict, dataclass
from pathlib import Path
import json


@dataclass(frozen=True)
class TrainingConfig:
    model_name: str = "microsoft/deberta-v3-small"
    max_length: int = 384
    train_batch_size: int = 4
    eval_batch_size: int = 16
    gradient_accumulation_steps: int = 4
    learning_rate: float = 2e-5
    epochs: int = 3
    weight_decay: float = 0.01
    warmup_ratio: float = 0.1
    max_grad_norm: float = 1.0
    seed: int = 42
    mixed_precision: bool = True
    use_context: bool = True          # False trains the stateless ablation (current event only)
    max_fpr: float = 0.05             # best epoch = highest val F1 among epochs with FPR <= this
    training_data: str = "data/training/mapis_phase4_events_v1.jsonl"
    output_dir: str = "artifacts/mapis_detector"

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(asdict(self), indent=2) + "\n", encoding="utf-8")
