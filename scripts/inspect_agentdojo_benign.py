import json
from pathlib import Path

root = Path("data/external/agentdojo/runs")
found = 0

for p in root.rglob("*.json"):
    with open(p, encoding="utf-8") as f:
        d = json.load(f)

    if d.get("attack_type"):
        continue

    messages = d.get("messages", [])
    if len(messages) < 3:
        continue

    print("\nPATH:", p.relative_to(root))
    print("Keys:", list(d.keys()))
    print("suite:", d.get("suite_name"))
    print("pipeline:", d.get("pipeline_name"))
    print("user_task:", d.get("user_task_id"))
    print("injection_task:", d.get("injection_task_id"))
    print("attack_type:", d.get("attack_type"))
    print("security:", d.get("security"))
    print("utility:", d.get("utility"))
    print("messages:", len(messages))
    print("roles:", [m.get("role") for m in messages][:15])

    found += 1
    if found >= 3:
        break
