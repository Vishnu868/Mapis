import json
from pathlib import Path
from collections import defaultdict

p = Path("data/mapis_bench/mapis_bench_v1.jsonl")

records = [
    json.loads(line)
    for line in p.open(encoding="utf-8")
    if line.strip()
]

groups = defaultdict(list)

for r in records:
    source = r["source_dataset"]
    rid = r["source_record_id"]

    if isinstance(rid, dict):
        key = (
            source,
            rid.get("suite_name"),
            rid.get("user_task_id"),
        )
    else:
        key = (source, str(rid))

    groups[key].append(r)

cross = {
    k: v for k, v in groups.items()
    if len({r["split"] for r in v}) > 1
}

print("Cross-split groups:", len(cross))
print()

for key, items in cross.items():
    print("GROUP:", key)
    print("Records:", len(items))

    for r in items:
        print(
            "  ",
            r["sample_id"],
            "| split:", r["split"],
            "| attack:", r["is_attack"],
            "| source_file:", r["source_file"]
        )

    print()
