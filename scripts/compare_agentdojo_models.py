import json
from pathlib import Path
from collections import defaultdict

root = Path("data/external/agentdojo/runs")

models = {}

for model_dir in root.iterdir():
    if not model_dir.is_dir():
        continue

    pairs = set()

    for p in model_dir.rglob("injection_task_*.json"):
        try:
            x = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue

        if any(
            m.get("role") == "tool"
            and isinstance(m.get("content"), str)
            and "<INFORMATION>" in m["content"]
            for m in x.get("messages", [])
        ):
            pairs.add(
                (
                    x.get("suite_name"),
                    x.get("user_task_id"),
                    x.get("injection_task_id"),
                    x.get("attack_type"),
                )
            )

    models[model_dir.name] = pairs

reference = models.get("claude-3-5-sonnet-20240620", set())

print("Models with embedded-injection trajectories:")
for name, pairs in models.items():
    if pairs:
        overlap = len(pairs & reference)
        print(f"{name}: {len(pairs)} candidates, {overlap} overlap with reference")

print()
print("Reference candidates:", len(reference))
