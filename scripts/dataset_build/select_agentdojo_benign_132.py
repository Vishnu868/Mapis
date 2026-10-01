import json
from pathlib import Path

root = Path("data/external/agentdojo/runs")
output = Path("data/mapis_multihop/agentdojo_benign_selected_132_keys.json")

groups = {}

for p in root.rglob("*.json"):
    with open(p, encoding="utf-8") as f:
        d = json.load(f)

    if d.get("attack_type"):
        continue

    if len(d.get("messages", [])) < 3:
        continue

    key = (d.get("suite_name"), d.get("user_task_id"))

    candidate = {
        "suite_name": d.get("suite_name"),
        "user_task_id": d.get("user_task_id"),
        "injection_task_id": d.get("injection_task_id"),
        "pipeline_name": d.get("pipeline_name"),
        "source_path": str(p.relative_to(root)).replace("/", "\\"),
    }

    if key not in groups:
        groups[key] = candidate
    elif candidate["pipeline_name"] == "gpt-4o-2024-05-13":
        groups[key] = candidate

records = sorted(
    groups.values(),
    key=lambda x: (x["suite_name"], x["user_task_id"])
)

result = {
    "dataset": "AgentDojo",
    "selection_type": "one_native_benign_trajectory_per_task_group",
    "selection_size": len(records),
    "selection_rule": "Prefer gpt-4o-2024-05-13 when available; otherwise first available pipeline.",
    "dedup_key": ["suite_name", "user_task_id"],
    "records": records,
}

output.parent.mkdir(parents=True, exist_ok=True)

with open(output, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2)

print("Selected benign groups:", len(records))
print("Output:", output)
print("Unique keys:", len(set((r["suite_name"], r["user_task_id"]) for r in records)))
