import json
from pathlib import Path

root = Path("data/external/agentdojo/runs")

def get_candidates(model):
    result = set()

    for p in (root / model).rglob("injection_task_*.json"):
        x = json.load(open(p, encoding="utf-8"))

        if not any(
            m.get("role") == "tool"
            and isinstance(m.get("content"), str)
            and "<INFORMATION>" in m["content"]
            for m in x.get("messages", [])
        ):
            continue

        result.add(
            (
                x.get("suite_name"),
                x.get("user_task_id"),
                x.get("injection_task_id"),
                x.get("attack_type"),
            )
        )

    return result


base = (
    get_candidates("claude-3-5-sonnet-20240620")
    | get_candidates("claude-3-7-sonnet-20250219")
)

print("Base unique combinations:", len(base))
print()

for model_dir in sorted(root.iterdir()):
    if not model_dir.is_dir():
        continue

    model = model_dir.name

    if model in {
        "claude-3-5-sonnet-20240620",
        "claude-3-7-sonnet-20250219",
    }:
        continue

    candidates = get_candidates(model)

    if candidates:
        new = len(candidates - base)
        print(f"{model}: total={len(candidates)}, new={new}")
