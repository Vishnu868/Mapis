import json
from pathlib import Path
from collections import defaultdict, Counter

root = Path("data/external/agentdojo/runs")
groups = defaultdict(set)

for p in root.rglob("*.json"):
    with open(p, encoding="utf-8") as f:
        d = json.load(f)

    if d.get("attack_type"):
        continue

    messages = d.get("messages", [])
    if len(messages) < 3:
        continue

    key = (d.get("suite_name"), d.get("user_task_id"))
    groups[key].add(d.get("pipeline_name"))

print("Unique benign groups:", len(groups))
print("Pipeline variants per group:", Counter(len(v) for v in groups.values()))

for key, pipelines in sorted(groups.items())[:20]:
    print(key, "=>", len(pipelines), sorted(pipelines))
