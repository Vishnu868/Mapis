import json
from collections import defaultdict

p = "data/mapis_bench/mapis_bench_v1_injecagent.jsonl"

records = []
with open(p, encoding="utf-8") as f:
    for line in f:
        if line.strip():
            x = json.loads(line)
            if x["is_attack"]:
                records.append(x)

d = defaultdict(set)

for x in records:
    instruction = x["messages"][2]["content"]
    d[instruction].add(x["source_label"]["attack_type"])

print("Unique attacker instructions:", len(d))
print()

for instruction, sources in d.items():
    print("SOURCE:", ", ".join(sorted(sources)))
    print("INSTRUCTION:", instruction)
    print("-" * 80)
