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
from backend.ml.data import attack_family, is_ood  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "mapis_bench" / "mapis_bench_v1.jsonl"
DEFAULT_OUTPUT = ROOT / "data" / "training" / "mapis_phase4_events_v2.jsonl"


def label_event(sample: dict[str, Any], hop: dict[str, Any], first_injection_hop: int | None = None) -> tuple[str, str, str]:
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
        # Hard negative: a tool output that came BEFORE the injected one in the same attacked session is clean
        # (same task, same tools, same environment) - the injection is localised to the tagged event.
        if (sample["source_dataset"] == "AgentDojo" and hop["role"] == "tool" and text.strip()
                and first_injection_hop is not None and hop["hop"] < first_injection_hop):
            return "safe", "event", "native_agentdojo_pre_injection_tool_output"
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


BENIGN_FILLER = [
    "Great product, arrived on time and works as described.", "Meeting moved to Thursday at 3pm, agenda unchanged.",
    "Thanks for the update, I will review the numbers tomorrow.", "Shipping took five days but packaging was fine.",
    "The battery lasts about a day with normal use.", "Quarterly report attached, please see page two for totals.",
    "Reminder: the team lunch is on Friday.", "Setup was easy and support answered quickly.",
    "Not what I expected, but the quality is acceptable for the price.", "Please find the revised schedule below.",
    "Looks good to me, no further changes needed.", "The room was clean and the staff were friendly.",
    "Delivery confirmed, tracking number sent separately.", "I use it every day and have had no problems so far.",
    "Draft notes from today's call are in the shared folder.", "Reservation confirmed for two guests next weekend.",
    "The screen is bright and the keyboard feels solid.", "Invoice paid, thank you for the quick service.",
    "Updated the document with the comments from last week.", "Would recommend to friends, five stars.",
    "The hotel was close to the station and breakfast was included.", "Can we push the call to next Monday morning?",
    "Fits well and the colour matches the photos.", "Thanks, the files opened fine on my side.",
    "The recipe was simple and the kids enjoyed it.", "Sales were up slightly compared with last month.",
    "Customer service replaced the item without any fuss.", "Parking was easy and the venue was spacious.",
    "Please confirm the delivery window for next week.", "The instructions were clear and assembly took twenty minutes.",
    "Lovely view from the room, would stay again.", "Budget review is scheduled for the end of the quarter.",
    "Sound quality is good, though the case feels a little cheap.", "Congratulations on the new role, well deserved.",
    "The tour guide was knowledgeable and funny.", "Attached is the signed copy for your records.",
    "It keeps drinks cold for most of the day.", "Thanks for the quick turnaround on the draft.",
    "The app is easy to use and syncs without problems.", "Looking forward to seeing everyone at the offsite.",
]
FILLER_POOL_BY_SPLIT = {"train": range(0, 24), "validation": range(24, 32), "test": range(32, len(BENIGN_FILLER)), "test_ood": range(32, len(BENIGN_FILLER))}


def clean_twins(sample: dict[str, Any], hops: list[dict[str, Any]], max_context_hops: int) -> list[dict[str, Any]]:
    """Minimal pairs for InjecAgent: the same tool response with the attacker instruction swapped for neutral text.

    Only the injected sentence differs, so a classifier cannot separate pair members by role, template, tool
    or length; it has to read the instruction. The filler is synthetic and labelled as such.
    """
    if sample["source_dataset"] != "InjecAgent" or not sample["is_attack"]:
        return []
    instruction = next((h["content"] for h in hops if h["role"] == "attacker_instruction" and h["content"]), None)
    tool_index = next((i for i, h in enumerate(hops) if h["role"] == "tool_response"), None)
    if not instruction or tool_index is None:
        return []
    seed = int(hashlib.sha256(sample["sample_id"].encode()).hexdigest()[:8], 16)
    pool = FILLER_POOL_BY_SPLIT[sample["split"]]  # sentences never shared across splits, so they cannot be memorised as "safe"
    filler = BENIGN_FILLER[pool[seed % len(pool)]]
    swapped = {}
    for key in ("content", "tool_response"):
        value = hops[tool_index][key]
        if not isinstance(value, str) or instruction not in value:
            return []
        swapped[key] = value.replace(instruction, filler)
    current = {**hops[tool_index], **swapped}
    context = rolling_context(hops, tool_index, max_context_hops)
    example_id = hashlib.sha256(f"phase4-v2-twin|{sample['sample_id']}".encode()).hexdigest()[:24]
    return [{
        "example_id": example_id, "source_sample_id": sample["sample_id"], "source_dataset": sample["source_dataset"], "attack_family": attack_family(sample),
        "source_record_id": sample["source_record_id"], "split": sample["split"], "label": "safe", "label_granularity": "event",
        "label_source": "derived_injecagent_clean_twin_synthetic_filler", "attack_class": None, "native_or_derived": "derived",
        "provenance": sample["provenance"], "current_hop": current, "context_hops": context, "text": build_text(context, current),
    }]


def build_examples(samples: list[dict[str, Any]], max_context_hops: int = 6) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    for sample in samples:
        sample = {**sample, "split": "test_ood" if is_ood(sample) else sample["split"]}
        hops = [normalize_hop(message) for message in sample["messages"]]
        first_injection = next((h["hop"] for h in hops if h["role"] == "tool" and "<INFORMATION>" in (h["content"] or "")), None)
        examples.extend(clean_twins(sample, hops, max_context_hops))
        for index, current in enumerate(hops):
            context = rolling_context(hops, index, max_context_hops)
            label, granularity, label_source = label_event(sample, current, first_injection)
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
                "attack_family": attack_family(sample),
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
