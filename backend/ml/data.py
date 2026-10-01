"""Supervised Phase-4 examples. 'unlabeled' records are never promoted to a label."""

from __future__ import annotations

import json
import re
from pathlib import Path

from backend.core.context import build_text

MARKERS = re.compile(r"</?INFORMATION>", re.I)  # AgentDojo wrapper tag: a dataset artifact, not injection semantics
LABELS = {"malicious": 0, "safe": 1}  # class 1 = SAFE, so P(class 1) is the trust score


def _text(ex: dict, use_context: bool) -> str:
    text = ex["text"] if use_context else build_text([], ex["current_hop"], (ex["chunk_index"], ex["n_chunks"]))
    return MARKERS.sub("", text)  # no-op for the committed pipeline; guards against hand-made files


def load_rows(path: str | Path, split: str, use_context: bool = True) -> list[dict]:
    """Supervised CHUNK rows of a split (training and validation). 'unlabeled' rows are never promoted to a label."""
    rows = []
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            ex = json.loads(line) if line.strip() else None
            if not ex or ex["split"] != split or ex["label"] not in LABELS:
                continue
            rows.append({"id": ex["example_id"], "text": _text(ex, use_context), "label": LABELS[ex["label"]],
                         "attack_class": ex.get("attack_class"), "attack_family": ex.get("attack_family"),
                         "source": ex["source_dataset"], "role": ex["current_hop"]["role"]})
    return rows


def load_events(path: str | Path, split: str, use_context: bool = True) -> list[dict]:
    """Supervised EVENTS of a split, each with ALL its chunk texts. Event trust = min over chunks, label = event label."""
    events: dict[str, dict] = {}
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            ex = json.loads(line) if line.strip() else None
            if not ex or ex["split"] != split or ex["event_label"] not in LABELS:
                continue
            ev = events.setdefault(ex["event_id"], {"id": ex["event_id"], "label": LABELS[ex["event_label"]], "texts": [],
                                                    "attack_class": ex.get("attack_class"), "attack_family": ex.get("attack_family"),
                                                    "source": ex["source_dataset"], "role": ex["current_hop"]["role"], "text": None})
            ev["texts"].append(_text(ex, use_context))
    for ev in events.values():
        ev["text"] = ev["texts"][0]  # representative text for the cheap baselines
    return list(events.values())


OOD_AGENTDOJO_FAMILIES = {"tool_knowledge"}  # attack templates never seen in training
OOD_INJECAGENT_BUCKET = 4                    # attacker instructions with hash % 4 == 0 are held out


def _instruction_hash(text: str) -> int:
    import hashlib
    return int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)


def attack_family(sample: dict) -> str | None:
    """Template family of an attack session (None for benign)."""
    if not sample["is_attack"]:
        return None
    if sample["source_dataset"] == "BIPIA":
        return f"bipia_{sample['source_label'].get('attack_category')}"
    if sample["source_dataset"] == "AgentDojo":
        t = str(sample["source_record_id"].get("attack_type"))
        return "important_instructions" if t.startswith("important_instructions") else t
    instruction = next((m["content"] for m in sample["messages"] if m["role"] == "attacker_instruction" and m["content"]), "")
    return f"injecagent_instruction_{_instruction_hash(instruction) % OOD_INJECAGENT_BUCKET}"


def is_ood(sample: dict) -> bool:
    """True for attack sessions whose template is held out from train/validation entirely."""
    fam = attack_family(sample)
    return bool(fam) and (fam in OOD_AGENTDOJO_FAMILIES or fam == f"injecagent_instruction_0")
