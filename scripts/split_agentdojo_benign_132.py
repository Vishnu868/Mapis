from pathlib import Path
import json
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "mapis_multihop" / "agentdojo_benign_132_raw.jsonl"
OUTPUT = ROOT / "data" / "mapis_multihop" / "agentdojo_benign_132.jsonl"

records = []

with open(INPUT, encoding="utf-8") as f:
    for line in f:
        if line.strip():
            records.append(json.loads(line))

groups = defaultdict(list)

for record in records:
    key = (
        record["source_record_id"]["suite_name"],
        record["source_record_id"]["user_task_id"],
    )
    groups[key].append(record)

# Deterministic ordering.
ordered_groups = sorted(groups.items(), key=lambda x: (x[0][0], x[0][1]))

# Approximate 70/15/15 split, preserving whole task groups.
n = len(ordered_groups)
train_end = round(n * 0.70)
val_end = train_end + round(n * 0.15)

split_map = {}

for i, (key, _) in enumerate(ordered_groups):
    if i < train_end:
        split_map[key] = "train"
    elif i < val_end:
        split_map[key] = "validation"
    else:
        split_map[key] = "test"

for record in records:
    key = (
        record["source_record_id"]["suite_name"],
        record["source_record_id"]["user_task_id"],
    )
    record["split"] = split_map[key]

with open(OUTPUT, "w", encoding="utf-8") as f:
    for record in records:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

print("Records:", len(records))
print("Groups:", len(groups))
print("Train groups:", sum(v == "train" for v in split_map.values()))
print("Validation groups:", sum(v == "validation" for v in split_map.values()))
print("Test groups:", sum(v == "test" for v in split_map.values()))
print("Train records:", sum(r["split"] == "train" for r in records))
print("Validation records:", sum(r["split"] == "validation" for r in records))
print("Test records:", sum(r["split"] == "test" for r in records))
print("Output:", OUTPUT)
