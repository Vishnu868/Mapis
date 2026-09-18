"""Validation for the derived Phase 4 MAPIS event dataset."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

try:  # works both as ``python scripts/...`` and as an imported test module
    from prepare_phase4_training_data import DEFAULT_OUTPUT, statistics
except ModuleNotFoundError:
    from scripts.prepare_phase4_training_data import DEFAULT_OUTPUT, statistics


VALID_LABELS = {"malicious", "safe", "unlabeled"}
VALID_SPLITS = {"train", "validation", "test"}


def load_examples(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def validate_examples(examples: list[dict]) -> dict:
    errors: list[str] = []
    ids = [example.get("example_id") for example in examples]
    if len(ids) != len(set(ids)):
        errors.append("duplicate example IDs")
    for example in examples:
        prefix = example.get("example_id", "<missing>")
        if example.get("label") not in VALID_LABELS:
            errors.append(f"{prefix}: invalid label")
        if example.get("split") not in VALID_SPLITS:
            errors.append(f"{prefix}: invalid split")
        if not example.get("source_sample_id") or "source_record_id" not in example:
            errors.append(f"{prefix}: source IDs not preserved")
        if not isinstance(example.get("provenance"), dict) or not example.get("native_or_derived"):
            errors.append(f"{prefix}: provenance/native-derived missing")
        current = example.get("current_hop", {})
        context = example.get("context_hops", [])
        if any(hop.get("hop", 0) >= current.get("hop", 0) for hop in context):
            errors.append(f"{prefix}: future-hop leakage")
        if current.get("content_state") == "null_assistant_tool_call" and example.get("label") != "unlabeled":
            errors.append(f"{prefix}: null assistant tool call supervised")
        if example.get("label") == "malicious" and example.get("label_source") == "attack_session_label_not_copied_to_hop":
            errors.append(f"{prefix}: attack session automatically labeled positive")
        if "<Attacker Instruction>" in str(current.get("content")) and not example.get("source_sample_id", "").startswith("injecagent_benign_"):
            pass
        elif "<Attacker Instruction>" in str(current.get("content")) and example.get("label") != "unlabeled":
            errors.append(f"{prefix}: benign InjecAgent placeholder supervised")

    supervised_sources = {example["source_sample_id"] for example in examples if example["label"] in {"malicious", "safe"}}
    split_by_source: dict[str, set[str]] = {}
    for example in examples:
        split_by_source.setdefault(example["source_sample_id"], set()).add(example["split"])
    if any(len(splits) > 1 for splits in split_by_source.values()):
        errors.append("a source sample crosses train/validation/test")

    report = {"valid": not errors, "errors": errors, "statistics": statistics(examples), "supervised_source_samples": len(supervised_sources)}
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = validate_examples(load_examples(args.input))
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["valid"] else 1)
