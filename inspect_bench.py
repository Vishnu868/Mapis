import json
from collections import Counter

path = "data/mapis_bench/mapis_bench_v1.jsonl"

records = []
with open(path, encoding="utf-8") as f:
    for line in f:
        records.append(json.loads(line))

print("Records:", len(records))
print("Attack:", sum(r["is_attack"] for r in records))
print("Benign:", sum(not r["is_attack"] for r in records))

hop_counts = Counter(len(r["messages"]) for r in records)

print("\nMessages per session:")
for hops, count in sorted(hop_counts.items()):
    print(f"  {hops} messages: {count} sessions")

print("\nSplits:")
print(Counter(r["split"] for r in records))

print("\nAttack classes:")
print(Counter(
    r["mapis_attack_class"]
    for r in records
    if r["is_attack"]
))
