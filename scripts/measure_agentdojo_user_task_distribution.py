import json
from pathlib import Path
from collections import Counter

root = Path("data/external/agentdojo/runs")

counts = Counter()

for p in root.rglob("injection_task_*.json"):
    x = json.load(open(p, encoding="utf-8"))

    if not any(
        m.get("role") == "tool"
        and isinstance(m.get("content"), str)
        and "<INFORMATION>" in m["content"]
        for m in x.get("messages", [])
    ):
        continue

    key = (x.get("suite_name"), x.get("user_task_id"))
    counts[key] += 1

print("Unique suite/user-task pairs:", len(counts))
print()
print("Top 20 user tasks by native injection trajectories:")

for (suite, task), count in counts.most_common(20):
    print(f"{suite:12} {task:15} {count}")
