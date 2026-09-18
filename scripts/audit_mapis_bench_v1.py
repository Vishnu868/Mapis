import json
from pathlib import Path
from collections import defaultdict, Counter

p = Path("data/mapis_bench/mapis_bench_v1.jsonl")

records = [
    json.loads(line)
    for line in p.open(encoding="utf-8")
    if line.strip()
]

checks = {}

# 1. IDs
ids = [r["sample_id"] for r in records]
checks["unique_sample_ids"] = len(ids) == len(set(ids))

# 2. Required high-level fields
required = [
    "sample_id",
    "source_dataset",
    "source_file",
    "source_record_id",
    "provenance",
    "split",
    "is_attack",
    "source_label",
    "mapis_attack_class",
    "representation_type",
    "messages",
]

checks["required_fields"] = all(
    all(field in r for field in required)
    for r in records
)

# 3. Message structure
message_ok = True
for r in records:
    messages = r["messages"]

    if not messages:
        message_ok = False
        break

    hops = [m.get("hop") for m in messages]

    if hops != list(range(1, len(messages) + 1)):
        message_ok = False
        break

    for m in messages:
        if not all(k in m for k in ["hop", "role", "source", "target", "content"]):
            message_ok = False
            break

checks["message_structure"] = message_ok

# 4. Split validity
checks["valid_splits"] = all(
    r["split"] in {"train", "validation", "test"}
    for r in records
)

# 5. Attack/benign label consistency
checks["benign_class_null"] = all(
    r["mapis_attack_class"] is None
    for r in records
    if not r["is_attack"]
)

# 6. Attack class validity
valid_classes = {
    "data_exfiltration",
    "financial_manipulation",
    "code_tool_manipulation",
    "instruction_override",
    "physical_safety_harm",
}

checks["valid_attack_classes"] = all(
    r["mapis_attack_class"] in valid_classes
    for r in records
    if r["is_attack"] and r["mapis_attack_class"] is not None
)

# 7. Source-specific group leakage
groups = defaultdict(set)

for r in records:
    source = r["source_dataset"]
    rid = r["source_record_id"]

    if isinstance(rid, dict):
        if source == "AgentDojo":
            key = (
                source,
                rid.get("suite_name"),
                rid.get("user_task_id"),
            )
        else:
            key = (
                source,
                rid.get("suite_name"),
                rid.get("user_task_id"),
            )
    else:
        key = (source, str(rid))

    groups[key].add(r["split"])

cross_split_groups = {
    k: v for k, v in groups.items()
    if len(v) > 1
}

checks["no_group_split_leakage"] = len(cross_split_groups) == 0

print("MAPIS-Bench v1 Integrity Audit")
print("=" * 40)
print("Records:", len(records))
print("Unique sample IDs:", len(set(ids)))
print("Sources:", Counter(r["source_dataset"] for r in records))
print("Attack/benign:", Counter(r["is_attack"] for r in records))
print("Splits:", Counter(r["split"] for r in records))
print("Representation:", Counter(r["representation_type"] for r in records))
print("Cross-split groups:", len(cross_split_groups))
print()

for name, result in checks.items():
    print(f"{name}: {'PASS' if result else 'FAIL'}")

print()
print(
    "OVERALL:",
    "PASS" if all(checks.values()) else "FAIL"
)
