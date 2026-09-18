import json
from pathlib import Path
from collections import defaultdict

root = Path("data/external/agentdojo/runs")

counts = defaultdict(lambda: defaultdict(int))

for p in root.rglob("injection_task_*.json"):
    x = json.load(open(p, encoding="utf-8"))

    if not any(
        m.get("role") == "tool"
        and isinstance(m.get("content"), str)
        and "<INFORMATION>" in m["content"]
        for m in x.get("messages", [])
    ):
        continue

    suite = x.get("suite_name")
    task = x.get("user_task_id")
    counts[suite][task] += 1

for suite in sorted(counts):
    values = list(counts[suite].values())
    print(
        f"{suite}: tasks={len(values)}, "
        f"total={sum(values)}, "
        f"min={min(values)}, "
        f"max={max(values)}, "
        f"avg={sum(values)/len(values):.1f}"
    )
