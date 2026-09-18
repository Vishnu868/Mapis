"""Loading utilities for supervised Phase 4 examples only."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


LABEL_TO_ID = {"malicious": 0, "safe": 1}


def load_examples(path: str | Path, split: str | None = None, supervised_only: bool = True) -> list[dict]:
    """Load prepared examples without ever promoting unlabeled records."""
    examples: list[dict] = []
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            example = json.loads(line)
            if split is not None and example["split"] != split:
                continue
            if supervised_only and example["label"] not in LABEL_TO_ID:
                continue
            examples.append(example)
    return examples


def labelled_rows(examples: Iterable[dict]) -> list[dict]:
    """Return the stable text/label payload consumed by the classifier."""
    return [
        {"example_id": ex["example_id"], "text": ex["text"], "label": LABEL_TO_ID[ex["label"]]}
        for ex in examples
        if ex["label"] in LABEL_TO_ID
    ]
