import json
from collections import Counter

path = "data/mapis_bench/mapis_bench_v1.jsonl"

for split in ["train", "validation", "test"]:
    role_counts = Counter()
    edge_counts = Counter()

    with open(path, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)

            if r["split"] != split:
                continue

            for m in r["messages"]:
                role_counts[m["role"]] += 1
                edge_counts[f"{m['source']} -> {m['target']}"] += 1

    print(f"\n{split.upper()}")
    print("Roles:", role_counts)
    print("Top communication edges:")
    for edge, count in edge_counts.most_common(15):
        print(f"  {edge}: {count}")
