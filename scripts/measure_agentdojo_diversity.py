import json
from pathlib import Path
from collections import Counter

root = Path("data/external/agentdojo/runs")

payloads = set()
user_tasks = set()
pairs = set()
attack_types = Counter()
suites = Counter()

for p in root.rglob("injection_task_*.json"):
    x = json.load(open(p, encoding="utf-8"))
    messages = x.get("messages", [])

    if not any(
        m.get("role") == "tool"
        and isinstance(m.get("content"), str)
        and "<INFORMATION>" in m["content"]
        for m in messages
    ):
        continue

    attack_types[x.get("attack_type")] += 1
    suites[x.get("suite_name")] += 1

    for value in x.get("injections", {}).values():
        if isinstance(value, str):
            payloads.add(value.strip())

    user_tasks.add(
        (
            x.get("suite_name"),
            x.get("user_task_id")
        )
    )

    pairs.add(
        (
            x.get("suite_name"),
            x.get("user_task_id"),
            x.get("attack_type")
        )
    )

print("Native embedded trajectories:", sum(attack_types.values()))
print("Unique injection payloads:", len(payloads))
print("Unique suite/user-task pairs:", len(user_tasks))
print("Unique suite/user-task/attack-type pairs:", len(pairs))
print()
print("Attack types:")
for k, v in attack_types.most_common():
    print(f"  {k}: {v}")
print()
print("Suites:")
for k, v in suites.most_common():
    print(f"  {k}: {v}")
