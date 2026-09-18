import json
from collections import defaultdict

p = "data/mapis_multihop/agentdojo_1000_raw.jsonl"

rows = [
    json.loads(x)
    for x in open(p, encoding="utf-8")
    if x.strip()
]

groups = defaultdict(list)

for r in rows:
    groups[r["source_label"]["attack_type"]].append(r)

for attack_type, records in sorted(groups.items()):
    print("\n===" + attack_type + "===")
    print("Count:", len(records))

    injection = next(
        (
            m.get("content")
            for r in records
            for m in r["messages"]
            if m.get("role") == "tool"
            and "<INFORMATION>" in (m.get("content") or "")
        ),
        ""
    )

    print("Sample injection:")
    print(injection[:1000])
