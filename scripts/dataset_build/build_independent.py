"""Validate the team's hand-written sessions (data/independent/*.json) and build the independent TEST-ONLY benchmark.

Files named EXAMPLE_* are ignored. Output: data/mapis_bench/mapis_bench_independent_v1.jsonl (split = test, never used for training).

    python scripts/dataset_build/build_independent.py
"""

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC, OUT = ROOT / "data" / "independent", ROOT / "data" / "mapis_bench" / "mapis_bench_independent_v1.jsonl"
ROLES = {"user", "assistant", "tool", "tool_response", "memory_read", "memory_write", "system"}
CLASSES = {"data_exfiltration", "financial_manipulation", "code_tool_manipulation", "instruction_override", "physical_safety_harm"}
VECTORS = {"document_poisoning", "memory_injection", "tool_output_manipulation", "cross_agent_injection", "goal_hijacking"}
KINDS = {"authorized", "resisted", "designated", "normal"}


def check(s: dict, where: str) -> list[str]:
    err = []
    if not isinstance(s.get("messages"), list) or len(s["messages"]) < 3:
        err.append("needs at least 3 messages")
    if s.get("is_attack") is True:
        if s.get("attack_class") not in CLASSES: err.append(f"attack_class must be one of {sorted(CLASSES)}")
        if s.get("attack_vector") not in VECTORS: err.append(f"attack_vector must be one of {sorted(VECTORS)}")
    elif s.get("is_attack") is False:
        if s.get("benign_kind") not in KINDS: err.append(f"benign_kind must be one of {sorted(KINDS)}")
    else:
        err.append("is_attack must be true or false")
    for i, m in enumerate(s.get("messages") or [], 1):
        if m.get("role") not in ROLES: err.append(f"message {i}: role must be one of {sorted(ROLES)}")
        if not m.get("source") or not m.get("target"): err.append(f"message {i}: source and target are required")
        if m.get("role") == "assistant" and m.get("tool_name") and not isinstance(m.get("tool_call"), dict): err.append(f"message {i}: tool_call must be an object")
    if (s.get("messages") or [{}])[0].get("role") != "user": err.append("first message must be the user's request")
    return [f"{where} [{s.get('id')}]: {e}" for e in err]


rows, errors = [], []
for f in sorted(SRC.glob("*.json")):
    if f.name.startswith("EXAMPLE"):
        continue
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        errors.append(f"{f.name}: invalid JSON ({e})"); continue
    for s in data if isinstance(data, list) else [data]:
        errors += check(s, f.name)
        attack = s.get("is_attack") is True
        msgs = [{"hop": i, "role": m["role"], "source": m.get("source"), "target": m.get("target"), "content": m.get("content"),
                 "tool_name": m.get("tool_name"), "tool_call": m.get("tool_call"), "tool_response": None} for i, m in enumerate(s.get("messages") or [], 1)]
        rows.append({"sample_id": f"independent_{s.get('id')}", "source_dataset": "MAPIS-Independent", "source_file": f"data/independent/{f.name}",
                     "source_record_id": s.get("id"), "split": "test", "is_attack": attack, "source_label": {"attack": attack, "author": s.get("author")},
                     "benign_kind": None if attack else s.get("benign_kind"), "mapis_attack_class": s.get("attack_class") if attack else None,
                     "representation_type": "session_multihop", "session_id": f"ind-{s.get('id')}",
                     "event_labels": {str(i): m.get("label", "malicious" if attack and i == len(msgs) else "safe" if not attack else "unlabeled")
                                      for i, m in enumerate(s.get("messages") or [], 1)},
                     "completion_hop": len(msgs), "provenance": {"original_dataset": "MAPIS-Independent", "conversion_type": "hand_written",
                                                                  "attack_vector": s.get("attack_vector") if attack else None, "depth": 0,
                                                                  "author": s.get("author")},
                     "messages": msgs, "conversion_notes": s.get("notes", "")})
if errors:
    print("FIX THESE BEFORE BUILDING:\n  " + "\n  ".join(errors)); sys.exit(1)
ids = [r["sample_id"] for r in rows]
if len(ids) != len(set(ids)):
    print("duplicate ids:", [i for i, c in Counter(ids).items() if c > 1]); sys.exit(1)
OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
print(f"wrote {len(rows)} sessions to {OUT}:", dict(Counter("attack" if r["is_attack"] else f"benign/{r['benign_kind']}" for r in rows)),
      dict(Counter(r["mapis_attack_class"] for r in rows if r["is_attack"])))
