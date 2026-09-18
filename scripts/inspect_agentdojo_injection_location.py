import json
from pathlib import Path
from collections import Counter

root = Path("data/external/agentdojo/runs")

stats = Counter()

for p in root.rglob("injection_task_*.json"):
    x = json.load(open(p, encoding="utf-8"))
    messages = x.get("messages", [])

    embedded_roles = [
        m.get("role")
        for m in messages
        if isinstance(m.get("content"), str)
        and "<INFORMATION>" in m["content"]
    ]

    if embedded_roles:
        stats["embedded_trajectories"] += 1

        for role in set(embedded_roles):
            stats[f"embedded_in_{role}"] += 1

        if "tool" in embedded_roles:
            stats["tool_response_embedded"] += 1

        if "user" in embedded_roles:
            stats["user_embedded"] += 1

        if "assistant" in embedded_roles:
            stats["assistant_embedded"] += 1

print("Embedded injection location")
for k, v in stats.items():
    print(f"{k}: {v}")
