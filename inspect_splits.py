import json
from collections import Counter

path = "data/mapis_bench/mapis_bench_v1.jsonl"

for split in ["train", "validation", "test"]:
    records = []

    with open(path, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r["split"] == split:
                records.append(r)

    messages = sum(len(r["messages"]) for r in records)

    print(f"\n{split.upper()}")
    print("Sessions:", len(records))
    print("Attack:", sum(r["is_attack"] for r in records))
    print("Benign:", sum(not r["is_attack"] for r in records))
    print("Messages:", messages)
    print("Classes:", Counter(
        r["mapis_attack_class"]
        for r in records
        if r["is_attack"]
    ))
