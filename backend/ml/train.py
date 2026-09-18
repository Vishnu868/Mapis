"""Explicit training entry point; importing or testing this module never trains."""

from __future__ import annotations

import argparse
import random
from pathlib import Path
import json

import numpy as np
import torch
from torch.utils.data import DataLoader

from .config import TrainingConfig
from .dataset import labelled_rows, load_examples
from .model import load_model_and_tokenizer


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def train(config: TrainingConfig) -> None:
    """Run only when invoked as a deliberate CLI command, never automatically."""
    set_seed(config.seed)
    train_rows = labelled_rows(load_examples(config.training_data, "train"))
    validation_rows = labelled_rows(load_examples(config.training_data, "validation"))
    if not train_rows or not validation_rows:
        raise ValueError("Prepared supervised train and validation examples are required")

    model, tokenizer = load_model_and_tokenizer(config)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay)

    def collate(rows):
        encoded = tokenizer([row["text"] for row in rows], padding=True, truncation=True,
                            max_length=config.max_length, return_tensors="pt")
        encoded["labels"] = torch.tensor([row["label"] for row in rows])
        return {key: value.to(device) for key, value in encoded.items()}

    loader = DataLoader(train_rows, batch_size=config.train_batch_size, shuffle=True, collate_fn=collate)
    scaler = torch.amp.GradScaler("cuda", enabled=config.use_mixed_precision and device.type == "cuda")
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    config.save(output_dir / "training_config.json")

    def evaluate(rows):
        model.eval()
        correct = total = 0
        with torch.no_grad():
            for start in range(0, len(rows), config.eval_batch_size):
                batch = collate(rows[start:start + config.eval_batch_size])
                predicted = model(**batch).logits.argmax(dim=-1)
                correct += int((predicted == batch["labels"]).sum().item())
                total += len(batch["labels"])
        model.train()
        return {"accuracy": correct / total if total else 0.0, "examples": total}

    model.train()
    history = []
    for epoch in range(1, config.epochs + 1):
        optimizer.zero_grad(set_to_none=True)
        for step, batch in enumerate(loader, start=1):
            with torch.autocast(device_type=device.type, enabled=scaler.is_enabled()):
                loss = model(**batch).loss / config.gradient_accumulation_steps
            scaler.scale(loss).backward()
            if step % config.gradient_accumulation_steps == 0 or step == len(loader):
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad(set_to_none=True)
        validation = evaluate(validation_rows)
        history.append({"epoch": epoch, "validation": validation})
        if config.checkpoint_every_epoch:
            checkpoint = output_dir / f"checkpoint-epoch-{epoch}"
            model.save_pretrained(checkpoint)
            tokenizer.save_pretrained(checkpoint)
    (output_dir / "validation_history.json").write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")
    # The held-out test split is never loaded here.
    print(f"Training completed on {len(train_rows)} train examples; validation: {history[-1]['validation']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deliberate Phase 4 MAPIS training entry point")
    parser.add_argument("--run", action="store_true", help="required acknowledgement before training")
    args = parser.parse_args()
    if not args.run:
        raise SystemExit("No training started. Re-run with --run after reviewing the configuration.")
    train(TrainingConfig())
