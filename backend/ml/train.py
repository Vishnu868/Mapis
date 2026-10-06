"""Fine-tune the detector.  Train + validation only; the test split is never read here.

    python -m backend.ml.train --run                 # stateful model (causal window)
    python -m backend.ml.train --run --no-context \
        --output-dir artifacts/mapis_stateless       # stateless ablation for the comparison

After the last epoch it saves the best epoch (by validation F1 subject to FPR <= 5%),
fits a temperature on validation logits and writes calibration.json next to the model.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import random
import time
from pathlib import Path

from .config import TrainingConfig
from .data import load_rows
from .metrics import at_threshold, confusion, summarize


def seed_everything(seed: int) -> None:
    import numpy as np
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def fit_temperature(logits, labels) -> float:
    """Single-parameter temperature scaling by minimising validation NLL."""
    import torch

    labels = torch.tensor(labels)
    log_t = torch.zeros(1, requires_grad=True)
    opt = torch.optim.LBFGS([log_t], lr=0.1, max_iter=100)

    def closure():
        opt.zero_grad()
        loss = torch.nn.functional.cross_entropy(logits / log_t.exp(), labels)
        loss.backward()
        return loss

    opt.step(closure)
    return float(log_t.detach().exp().clamp(0.05, 20.0))


def train(cfg: TrainingConfig) -> dict:
    import torch
    from torch.utils.data import DataLoader
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup

    seed_everything(cfg.seed)
    print(f"[1/4] Loading data from {cfg.training_data} (can take up to a minute on a slow disk)...", flush=True)
    train_rows = load_rows(cfg.training_data, "train", cfg.use_context)
    val_rows = load_rows(cfg.training_data, "validation", cfg.use_context)
    if not train_rows or not val_rows:
        raise SystemExit(f"No supervised train/validation rows found in {cfg.training_data}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"      {len(train_rows)} train / {len(val_rows)} validation chunk rows; device = {device}"
          + (f" ({torch.cuda.get_device_name(0)})" if device.type == "cuda" else "  <-- NO GPU: this will be very slow"), flush=True)
    print(f"[2/4] Loading {cfg.model_name} ...", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(cfg.model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        cfg.model_name, num_labels=2, id2label={0: "MALICIOUS", 1: "SAFE"}, label2id={"MALICIOUS": 0, "SAFE": 1},
        use_safetensors=True).float().to(device)
    if cfg.gradient_checkpointing:
        model.gradient_checkpointing_enable()  # safetensors loads on any torch version; .float(): new transformers loads fp16 weights, mixed precision needs fp32 masters

    def collate(rows):
        enc = tokenizer([r["text"] for r in rows], padding=True, truncation=True, max_length=cfg.max_length, return_tensors="pt")
        enc["labels"] = torch.tensor([r["label"] for r in rows])
        return enc

    loader = DataLoader(train_rows, batch_size=cfg.train_batch_size, shuffle=True, collate_fn=collate)
    steps = cfg.epochs * -(-len(loader) // cfg.gradient_accumulation_steps)
    no_decay = ("bias", "LayerNorm.weight")
    params = [{"params": [p for n, p in model.named_parameters() if not any(k in n for k in no_decay)], "weight_decay": cfg.weight_decay},
              {"params": [p for n, p in model.named_parameters() if any(k in n for k in no_decay)], "weight_decay": 0.0}]
    optimizer = torch.optim.AdamW(params, lr=cfg.learning_rate)
    scheduler = get_linear_schedule_with_warmup(optimizer, int(cfg.warmup_ratio * steps), steps)
    amp = cfg.mixed_precision and device.type == "cuda"
    scaler = torch.amp.GradScaler("cuda", enabled=amp)

    # Mild class weights: safe examples are the minority.
    counts = [sum(r["label"] == c for r in train_rows) for c in (0, 1)]
    weights = torch.tensor([len(train_rows) / (2 * max(n, 1)) for n in counts], device=device)

    out = Path(cfg.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    cfg.save(out / "training_config.json")
    print(f"[3/4] Training {cfg.epochs} epochs, {len(loader)} batches per epoch (a progress line every 100 batches)", flush=True)

    def validate():
        model.eval()
        logits = []
        with torch.inference_mode():
            for i in range(0, len(val_rows), cfg.eval_batch_size):
                batch = {k: v.to(device) for k, v in collate(val_rows[i:i + cfg.eval_batch_size]).items() if k != "labels"}
                logits.append(model(**batch).logits.float().cpu())
        model.train()
        logits = torch.cat(logits)
        trust = torch.softmax(logits, -1)[:, 1].tolist()
        labels = [r["label"] for r in val_rows]
        return logits, labels, summarize(confusion(labels, [t < 0.5 for t in trust]))

    history, best = [], (-1.0, None)
    model.train()
    start = time.time()
    for epoch in range(1, cfg.epochs + 1):
        optimizer.zero_grad(set_to_none=True)
        running = 0.0
        for step, batch in enumerate(loader, 1):
            labels = batch.pop("labels").to(device)
            batch = {k: v.to(device) for k, v in batch.items()}
            with torch.autocast(device_type=device.type, enabled=amp):
                logits = model(**batch).logits
            loss = torch.nn.functional.cross_entropy(logits.float(), labels, weight=weights) / cfg.gradient_accumulation_steps
            scaler.scale(loss).backward()
            running += loss.item() * cfg.gradient_accumulation_steps
            if step % 100 == 0:
                print(f"      epoch {epoch} batch {step}/{len(loader)}  loss {running / step:.4f}  ({time.time() - start:.0f}s elapsed)", flush=True)
            if step % cfg.gradient_accumulation_steps == 0 or step == len(loader):
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), cfg.max_grad_norm)
                scaler.step(optimizer)
                scaler.update()
                scheduler.step()
                optimizer.zero_grad(set_to_none=True)
        val_logits, val_labels, metrics = validate()
        history.append({"epoch": epoch, "train_loss": running / len(loader), "validation": metrics})
        print(f"epoch {epoch}: loss {running / len(loader):.4f} | val F1 {metrics['f1']:.4f} recall {metrics['recall']:.4f} FPR {metrics['fpr']:.4f}")
        score = metrics["f1"] if metrics["fpr"] <= cfg.max_fpr else metrics["f1"] - 1.0  # prefer epochs inside the FPR budget
        if score > best[0]:
            best = (score, epoch)
            model.save_pretrained(out)
            tokenizer.save_pretrained(out)
            best_logits, best_labels = val_logits, val_labels

    print("[4/4] Calibrating on validation ...", flush=True)
    temperature = fit_temperature(best_logits, best_labels)
    trust = torch.softmax(best_logits / temperature, -1)[:, 1].tolist()
    calibration = {"temperature": temperature, "max_length": cfg.max_length, "use_context": cfg.use_context,
                   "best_epoch": best[1], "validation_at_0.5": at_threshold(best_labels, trust, 0.5)}
    (out / "calibration.json").write_text(json.dumps(calibration, indent=2) + "\n")
    (out / "history.json").write_text(json.dumps(history, indent=2) + "\n")
    print(f"saved epoch {best[1]} to {out} (temperature {temperature:.3f}, {time.time() - start:.0f}s)")
    return calibration


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", action="store_true", help="required acknowledgement before training starts")
    ap.add_argument("--no-context", action="store_true", help="train the stateless ablation")
    ap.add_argument("--output-dir")
    ap.add_argument("--data")
    ap.add_argument("--model-name")
    ap.add_argument("--epochs", type=int)
    ap.add_argument("--seed", type=int)
    ap.add_argument("--base", action="store_true", help="deberta-v3-base, batch 2 x accumulation 8, gradient checkpointing")
    args = ap.parse_args()
    if not args.run:
        raise SystemExit("Nothing started. Re-run with --run.")
    over = {k: v for k, v in {"output_dir": args.output_dir, "training_data": args.data, "model_name": args.model_name,
                              "epochs": args.epochs, "seed": args.seed, "use_context": False if args.no_context else None}.items() if v is not None}
    if args.base:
        over = {"model_name": "microsoft/deberta-v3-base", "train_batch_size": 2, "gradient_accumulation_steps": 8, "gradient_checkpointing": True, **over}
    train(dataclasses.replace(TrainingConfig(), **over))
