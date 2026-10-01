"""Build the auditable, causal event representation for MAPIS Phase 4.

This script does not alter MAPIS-Bench.  It creates one record per source hop,
retaining unlabeled records for forensic review while supervised loading selects
only the evidence-backed ``malicious`` and policy-defined ``safe`` examples.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.core.context import build_text, normalize_hop, render_hop, rolling_context  # noqa: E402,F401


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "mapis_bench" / "mapis_bench_v1.jsonl"
DEFAULT_OUTPUT = ROOT / "data" / "training" / "mapis_phase4_events_v1.jsonl"


def label_event(sample: dict[str, Any], hop: dict[str, Any]) -> tuple[str, str, str]:
    """Return label, granularity, and evidence/policy source.

    Only localized injections are positive.  All other attack-session events
    remain unlabeled.  Safe labels are limited to native benign text events and
    non-placeholder InjecAgent benign user requests.
    """
    if hop["content_state"] == "null_assistant_tool_call":
        return "unlabeled", "event", "null_assistant_tool_call_excluded"

    text = hop["content"] if isinstance(hop["content"], str) else ""
    if sample["is_attack"]:
        if sample["source_dataset"] == "AgentDojo" and hop["role"] == "tool" and "<INFORMATION>" in text:
            return "malicious", "event", "native_agentdojo_embedded_tool_instruction"
        if sample["source_dataset"] == "InjecAgent" and hop["role"] == "tool_response":
            return "malicious", "event", "derived_injecagent_injection_bearing_tool_response"
        # The derived extraction is useful evidence but not a separate runtime event.
        if sample["source_dataset"] == "InjecAgent" and hop["role"] == "attacker_instruction":
            return "unlabeled", "event", "derived_instruction_extraction_not_runtime_event"
        return "unlabeled", "session", "attack_session_label_not_copied_to_hop"

    if sample["source_dataset"] == "InjecAgent" and "<Attacker Instruction>" in text:
        return "unlabeled", "event", "benign_injecagent_placeholder_excluded"
    if not text.strip():
        return "unlabeled", "event", "empty_benign_event_excluded"
    if sample["source_dataset"] == "AgentDojo":
        return "safe", "event", "native_benign_trajectory_text_policy"
    if sample["source_dataset"] == "InjecAgent" and hop["role"] == "user":
        return "safe", "event", "benign_injecagent_user_instruction_policy"
    return "unlabeled", "event", "benign_event_outside_safe_policy"


def build_examples(samples: list[dict[str, Any]], max_context_hops: int = 6) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    for sample in samples:
        hops = [normalize_hop(message) for message in sample["messages"]]
        for index, current in enumerate(hops):
            context = rolling_context(hops, index, max_context_hops)
            label, granularity, label_source = label_event(sample, current)
            example_id = hashlib.sha256(f"phase4-v1|{sample['sample_id']}|{current['hop']}".encode()).hexdigest()[:24]
            text = build_text(context, current)
            examples.append({
                "example_id": example_id,
                "source_sample_id": sample["sample_id"],
                "source_dataset": sample["source_dataset"],
                "source_record_id": sample["source_record_id"],
                "split": sample["split"],
                "label": label,
                "label_granularity": granularity,
                "label_source": label_source,
                "attack_class": sample["mapis_attack_class"],
                "native_or_derived": sample["provenance"]["conversion_type"],
                "provenance": sample["provenance"],
                "current_hop": current,
                "context_hops": context,
                "text": text,
            })
    return examples


def statistics(examples: list[dict[str, Any]]) -> dict[str, Any]:
    def count(field: str) -> dict[str, int]:
        return dict(sorted(Counter(str(example.get(field)) for example in examples).items()))
    return {
        "total_examples": len(examples),
        "labels": count("label"),
        "splits": count("split"),
        "source_dataset": count("source_dataset"),
        "native_or_derived": count("native_or_derived"),
        "label_granularity": count("label_granularity"),
        "attack_class": count("attack_class"),
        "label_source": count("label_source"),
    }


def load_samples(source: Path = SOURCE) -> list[dict[str, Any]]:
    with source.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_dataset(examples: list[dict[str, Any]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for example in examples:
            handle.write(json.dumps(example, ensure_ascii=False) + "\n")
    output.with_name(output.stem + "_stats.json").write_text(json.dumps(statistics(examples), indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-context-hops", type=int, default=6)
    args = parser.parse_args()
    examples = build_examples(load_samples(args.source), args.max_context_hops)
    write_dataset(examples, args.output)
    print(json.dumps(statistics(examples), indent=2))
