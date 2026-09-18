import json
from pathlib import Path
from collections import defaultdict, Counter

root = Path("data/external/agentdojo/runs")
counts = defaultdict(Counter)

for p in root.rglob("injection_task_*.json"):
    x = json.load(open(p, encoding="utf-8"))

    if not any(
        m.get("role") == "tool"
        and isinstance(m.get("content"), str)
        and "<INFORMATION>" in m["content"]
        for m in x.get("messages", [])
    ):
        continue

    counts[x.get("suite_name")][x.get("attack_type")] += 1

for suite in sorted(counts):
    print("=" * 60)
    print(suite)
    for attack_type, count in counts[suite].most_common():
        print(f"  {attack_type}: {count}")
