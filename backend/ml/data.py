"""Supervised Phase-4 examples. 'unlabeled' records are never promoted to a label."""

from __future__ import annotations

import json
from pathlib import Path

from backend.core.context import build_text

LABELS = {"malicious": 0, "safe": 1}  # class 1 = SAFE, so P(class 1) is the trust score


def load_rows(path: str | Path, split: str, use_context: bool = True) -> list[dict]:
    rows = []
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            ex = json.loads(line) if line.strip() else None
            if not ex or ex["split"] != split or ex["label"] not in LABELS:
                continue
            text = ex["text"] if use_context else build_text([], ex["current_hop"])
            rows.append({"id": ex["example_id"], "text": text, "label": LABELS[ex["label"]],
                         "attack_class": ex.get("attack_class"), "source": ex["source_dataset"], "role": ex["current_hop"]["role"]})
    return rows
