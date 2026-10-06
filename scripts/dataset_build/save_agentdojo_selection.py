import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "data" / "external" / "agentdojo" / "runs"
OUT = ROOT / "data" / "mapis_multihop" / "agentdojo_selected_1000_keys.json"

MODELS = [
    "claude-3-5-sonnet-20240620",
    "claude-3-7-sonnet-20250219",
    "gpt-4o-2024-05-13",
]

TARGET = 1000
records = {}

for model in MODELS:
    for path in (RUNS / model).rglob("injection_task_*.json"):
        with open(path, encoding="utf-8") as f:
            case = json.load(f)

        if not any(
            m.get("role") == "tool"
            and isinstance(m.get("content"), str)
            and "<INFORMATION>" in m["content"]
            for m in case.get("messages", [])
        ):
            continue

        key = (
            case.get("suite_name"),
            case.get("user_task_id"),
            case.get("injection_task_id"),
            case.get("attack_type"),
        )

        if key not in records:
            records[key] = {
                "suite_name": key[0],
                "user_task_id": key[1],
                "injection_task_id": key[2],
                "attack_type": key[3],
                "model": model,
                "source_path": str(path.relative_to(ROOT)),
            }

groups = {}
for key, record in records.items():
    groups.setdefault((key[0], key[3]), []).append((key, record))

for group in groups:
    groups[group].sort(key=lambda x: (str(x[0][1]), str(x[0][2])))

total = len(records)

raw = {
    group: len(items) * TARGET / total
    for group, items in groups.items()
}

allocations = {
    group: int(raw[group])
    for group in groups
}

remaining = TARGET - sum(allocations.values())

for group in sorted(
    groups,
    key=lambda g: (raw[g] - int(raw[g]), str(g)),
    reverse=True,
):
    if remaining == 0:
        break
    allocations[group] += 1
    remaining -= 1

selected = []

for group in sorted(groups):
    selected.extend(groups[group][:allocations[group]])

selected.sort(
    key=lambda x: (
        str(x[0][0]),
        str(x[0][3]),
        str(x[0][1]),
        str(x[0][2]),
    )
)

assert len(selected) == TARGET
assert len({x[0] for x in selected}) == TARGET

OUT.parent.mkdir(parents=True, exist_ok=True)

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(
        {
            "dataset": "AgentDojo",
            "selection_size": TARGET,
            "deduplication_key": [
                "suite_name",
                "user_task_id",
                "injection_task_id",
                "attack_type",
            ],
            "models_considered": MODELS,
            "records": [record for _, record in selected],
        },
        f,
        indent=2,
        ensure_ascii=False,
    )

print("Saved:", OUT)
print("Selected records:", len(selected))
print("Unique keys:", len({x[0] for x in selected}))
