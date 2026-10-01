"""Build the auditable, causal, CHUNKED event dataset (Phase 4, v3) from MAPIS-Bench.

One example per (event, chunk). Long events are split into overlapping chunks so the classifier sees the whole
event; the injection span is known for every attack, so the chunk that contains it is the positive and the other
chunks of the same event are hard negatives. The event label is kept (`event_label`) for event-level evaluation
(an event's trust = min over its chunks).

Sources: MAPIS-Bench v1 (AgentDojo + InjecAgent) and, when present, MAPIS-Bench BIPIA (minimal pairs).
Splits: train / validation / test as in the benchmark; template-held-out `test_ood`; BIPIA's own test -> `test_bipia`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.core.context import (CHUNK_CHARS, build_text, chunk_hop, chunk_spans, event_text, normalize_hop,  # noqa: E402
                                  rolling_context)
from backend.ml.data import MARKERS, attack_family, is_ood  # noqa: E402

SOURCES = [ROOT / "data/mapis_bench/mapis_bench_v1.jsonl", ROOT / "data/mapis_bench/mapis_bench_bipia_v1.jsonl"]
DEFAULT_OUTPUT = ROOT / "data" / "training" / "mapis_phase4_events_v3.jsonl"
SAFE_CHUNKS_PER_EVENT = 3     # cap on safe chunks kept per event (the rest are kept only for event-level evaluation)
NEG_CHUNKS_PER_INJECTED_EVENT = 2

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
FILLER_POOL_BY_SPLIT = {"train": range(0, 24), "validation": range(24, 32), "test": range(32, len(BENIGN_FILLER)),
                        "test_ood": range(32, len(BENIGN_FILLER)), "test_bipia": range(32, len(BENIGN_FILLER))}


def _h(*parts: str) -> int:
    return int(hashlib.sha256("|".join(parts).encode()).hexdigest()[:12], 16)


def _strip_tags(value: Any) -> Any:
    if isinstance(value, str):
        return MARKERS.sub("", value)
    if isinstance(value, list):
        return [_strip_tags(v) for v in value]
    if isinstance(value, dict):
        return {k: _strip_tags(v) for k, v in value.items()}
    return value


# ── preprocessing: strip dataset artifacts, locate every injection ───────────────────────
def clean_sample(sample: dict[str, Any]) -> tuple[dict[str, Any], dict[int, tuple[int, int]]]:
    """Remove the AgentDojo wrapper tag and return {hop: (start, end)} of the injected text in each poisoned event."""
    spans: dict[int, tuple[int, int]] = {}
    instruction = next((m["content"] for m in sample["messages"] if m["role"] == "attacker_instruction" and m["content"]), None)
    injected = (sample.get("source_label") or {}).get("injection_text")
    messages = []
    for m in sample["messages"]:
        m = dict(m)
        content = m.get("content")
        if sample["is_attack"] and isinstance(content, str):
            if sample["source_dataset"] == "AgentDojo" and m["role"] == "tool" and "<INFORMATION>" in content:
                i = content.index("<INFORMATION>")
                j = content.find("</INFORMATION>")
                inner = content[i + len("<INFORMATION>"): j if j >= 0 else len(content)]
                rest = content[j + len("</INFORMATION>"):] if j >= 0 else ""
                m["content"] = content[:i] + inner + rest
                spans[m["hop"]] = (i, i + len(inner))
            elif m["role"] == "tool_response":
                needle = instruction if sample["source_dataset"] == "InjecAgent" else injected
                at = content.find(needle) if needle else -1
                if at >= 0:
                    spans[m["hop"]] = (at, at + len(needle))
        for key in ("content", "tool_call", "tool_calls", "tool_response"):  # agents sometimes echo the tag inside call arguments
            m[key] = _strip_tags(m.get(key))
        messages.append(m)
    return {**sample, "messages": messages}, spans


# ── labelling policy (event level) ───────────────────────────────────────────────────────
def label_event(sample: dict[str, Any], hop: dict[str, Any], spans: dict[int, tuple[int, int]]) -> tuple[str, str]:
    """Return (label, source) for one event. Only localised injections are positive; attack-session labels are never copied."""
    if hop["content_state"] == "null_assistant_tool_call":
        return "unlabeled", "null_assistant_tool_call_excluded"
    text = hop["content"] if isinstance(hop["content"], str) else ""
    dataset = sample["source_dataset"]
    if sample["is_attack"]:
        if hop["hop"] in spans:
            return "malicious", {"AgentDojo": "native_agentdojo_embedded_tool_instruction",
                                 "InjecAgent": "derived_injecagent_injection_bearing_tool_response",
                                 "BIPIA": "bipia_poisoned_context"}[dataset]
        first = min(spans) if spans else None
        if dataset == "AgentDojo" and hop["role"] == "tool" and text.strip() and first is not None and hop["hop"] < first:
            return "safe", "native_agentdojo_pre_injection_tool_output"  # same task and tools, before the injection arrived
        if dataset == "InjecAgent" and hop["role"] == "attacker_instruction":
            return "unlabeled", "derived_instruction_extraction_not_runtime_event"
        return "unlabeled", "attack_session_label_not_copied_to_hop"
    if dataset == "InjecAgent" and "<Attacker Instruction>" in text:
        return "unlabeled", "benign_injecagent_placeholder_excluded"
    if not text.strip():
        return "unlabeled", "empty_benign_event_excluded"
    if dataset == "AgentDojo":
        return "safe", "native_benign_trajectory_text_policy"
    if dataset == "InjecAgent" and hop["role"] == "user":
        return "safe", "benign_injecagent_user_instruction_policy"
    if dataset == "BIPIA" and hop["role"] in ("user", "tool_response"):
        return "safe", "bipia_clean_context_policy"
    return "unlabeled", "benign_event_outside_safe_policy"


# ── chunk-level expansion ────────────────────────────────────────────────────────────────
def expand(sample: dict[str, Any], hops: list[dict[str, Any]], index: int, event_label: str, label_source: str,
           span: tuple[int, int] | None) -> list[dict[str, Any]]:
    hop = hops[index]
    context = rolling_context(hops, index)
    spans = chunk_spans(len(event_text(hop)))
    whole = len(spans) == 1
    event_id = hashlib.sha256(f"phase4-v3|{sample['sample_id']}|{hop['hop']}".encode()).hexdigest()[:20]

    labels = ["unlabeled"] * len(spans)
    sources = [f"{label_source}:chunk_not_selected"] * len(spans)
    if event_label == "safe":
        keep = sorted(range(len(spans)), key=lambda i: _h(event_id, str(i)))[:SAFE_CHUNKS_PER_EVENT]
        for i in keep:
            labels[i], sources[i] = "safe", label_source
    elif event_label == "malicious" and span:
        need = 0.6 * min(span[1] - span[0], CHUNK_CHARS)
        negatives = []
        for i, (s, e) in enumerate(spans):
            overlap = max(0, min(e, span[1]) - max(s, span[0]))
            if overlap >= need or whole:
                labels[i], sources[i] = "malicious", label_source
            elif overlap == 0:
                negatives.append(i)
            else:
                sources[i] = f"{label_source}:chunk_partially_overlaps_injection"
        for i in sorted(negatives, key=lambda i: _h(event_id, str(i)))[:NEG_CHUNKS_PER_INJECTED_EVENT]:
            labels[i], sources[i] = "safe", "chunk_of_injected_event_without_injection"

    examples = []
    for i, (s, e) in enumerate(spans):
        if event_label == "unlabeled" and i > 0:
            break  # unlabeled events are retained for forensics only; one row is enough
        current = chunk_hop(hop, s, e, whole)
        examples.append({
            "example_id": hashlib.sha256(f"{event_id}|{i}".encode()).hexdigest()[:24], "event_id": event_id,
            "chunk_index": i + 1, "n_chunks": len(spans), "event_label": event_label,
            "source_sample_id": sample["sample_id"], "source_dataset": sample["source_dataset"],
            "source_record_id": sample["source_record_id"], "split": sample["split"],
            "label": labels[i], "label_granularity": "chunk", "label_source": sources[i],
            "attack_class": sample["mapis_attack_class"], "attack_family": attack_family(sample),
            "native_or_derived": sample["provenance"]["conversion_type"], "provenance": sample["provenance"],
            "current_hop": current, "context_hops": context, "text": build_text(context, current, (i + 1, len(spans))),
        })
    return examples


def clean_twins(sample: dict[str, Any], hops: list[dict[str, Any]], spans: dict[int, tuple[int, int]]) -> list[dict[str, Any]]:
    """InjecAgent minimal pairs: the same tool response with the attacker instruction replaced by neutral text.

    Only the injected sentence differs, so a classifier cannot separate pair members by role, template, tool or
    length. The filler is synthetic, labelled as such, and drawn from a pool that is disjoint per split.
    """
    if sample["source_dataset"] != "InjecAgent" or not sample["is_attack"] or not spans:
        return []
    index = next(i for i, h in enumerate(hops) if h["hop"] in spans)
    a, b = spans[hops[index]["hop"]]
    pool = FILLER_POOL_BY_SPLIT[sample["split"]]
    filler = BENIGN_FILLER[pool[_h(sample["sample_id"]) % len(pool)]]
    twin_hops = [dict(h) for h in hops]
    for key in ("content", "tool_response"):
        value = twin_hops[index][key]
        if isinstance(value, str) and value[a:b] == hops[index]["content"][a:b]:
            twin_hops[index][key] = value[:a] + filler + value[b:]
    twin_sample = {**sample, "sample_id": sample["sample_id"] + "|clean_twin", "mapis_attack_class": None, "is_attack": False}
    twin = expand({**twin_sample, "sample_id": sample["sample_id"]}, twin_hops, index, "safe", "derived_injecagent_clean_twin_synthetic_filler", None)
    for e in twin:  # distinct ids from the attacked event of the same session
        e["event_id"] = e["event_id"][:-4] + "twin"
        e["example_id"] = hashlib.sha256((e["example_id"] + "twin").encode()).hexdigest()[:24]
        e["native_or_derived"], e["attack_family"] = "derived", None
    return twin


def build_examples(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    for sample in samples:
        split = "test_ood" if is_ood(sample) else "test_bipia" if sample["split"] == "external" else sample["split"]
        sample, spans = clean_sample({**sample, "split": split})
        hops = [normalize_hop(m) for m in sample["messages"]]
        examples.extend(clean_twins(sample, hops, spans))
        for index, hop in enumerate(hops):
            label, source = label_event(sample, hop, spans)
            examples.extend(expand(sample, hops, index, label, source, spans.get(hop["hop"])))
    return examples


def statistics(examples: list[dict[str, Any]]) -> dict[str, Any]:
    def count(field: str, rows=examples) -> dict[str, int]:
        return dict(sorted(Counter(str(e.get(field)) for e in rows).items()))
    events = {e["event_id"]: e for e in examples}.values()
    sup = [e for e in events if e["event_label"] in ("malicious", "safe")]
    return {
        "total_examples": len(examples), "chunk_labels": count("label"), "splits_chunks": count("split"),
        "events_supervised": count("event_label", sup), "events_supervised_by_split_and_label":
            dict(sorted(Counter(f"{e['split']}/{e['event_label']}" for e in sup).items())),
        "source_dataset": count("source_dataset"), "native_or_derived": count("native_or_derived"),
        "attack_class_events": count("attack_class", [e for e in sup if e["event_label"] == "malicious"]),
        "label_source": count("label_source"),
    }


def load_samples(*sources: Path) -> list[dict[str, Any]]:
    samples = []
    for source in sources:
        if source.exists():
            with source.open(encoding="utf-8") as handle:
                samples += [json.loads(line) for line in handle if line.strip()]
    return samples


def write_dataset(examples: list[dict[str, Any]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for example in examples:
            handle.write(json.dumps(example, ensure_ascii=False) + "\n")
    output.with_name(output.stem + "_stats.json").write_text(json.dumps(statistics(examples), indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, nargs="*", default=SOURCES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    examples = build_examples(load_samples(*args.source))
    write_dataset(examples, args.output)
    print(json.dumps(statistics(examples), indent=2))
