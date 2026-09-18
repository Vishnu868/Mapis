import json
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "data" / "external" / "agentdojo" / "runs"

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

        messages = case.get("messages", [])

        if not any(
            m.get("role") == "tool"
            and isinstance(m.get("content"), str)
            and "<INFORMATION>" in m["content"]
            for m in messages
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
                "model": model,
                "path": str(path.relative_to(ROOT)),
                "case": case,
            }

print("Unique trajectories:", len(records))

# Group by (suite, attack_type)
groups = defaultdict(list)

for key, record in records.items():
    groups[(key[0], key[3])].append((key, record))

# Stable ordering within every group.
for group in groups:
    groups[group].sort(
        key=lambda item: (
            str(item[0][1]),
            str(item[0][2]),
        )
    )

# Proportional allocation using largest-remainder method.
total = len(records)
allocations = {}

raw = {
    group: len(items) * TARGET / total
    for group, items in groups.items()
}

for group, value in raw.items():
    allocations[group] = min(len(groups[group]), int(value))

remaining = TARGET - sum(allocations.values())

remainders = sorted(
    groups,
    key=lambda g: (raw[g] - int(raw[g]), str(g)),
    reverse=True,
)

for group in remainders:
    if remaining == 0:
        break
    if allocations[group] < len(groups[group]):
        allocations[group] += 1
        remaining -= 1

selected = []

for group in sorted(groups):
    selected.extend(groups[group][:allocations[group]])

# Final deterministic ordering.
selected.sort(
    key=lambda item: (
        str(item[0][0]),
        str(item[0][3]),
        str(item[0][1]),
        str(item[0][2]),
    )
)

print("Selected:", len(selected))
print("Remaining:", total - len(selected))

print("\nSuite distribution:")
suite_counts = Counter(key[0] for key, _ in selected)
for suite, count in sorted(suite_counts.items()):
    full = Counter(key[0] for key in records)[suite]
    print(f"  {suite}: {count}/{full} ({count / TARGET:.1%})")

print("\nAttack-type distribution:")
attack_counts = Counter(key[3] for key, _ in selected)
full_attack_counts = Counter(key[3] for key in records)

for attack_type, count in sorted(attack_counts.items()):
    full = full_attack_counts[attack_type]
    print(f"  {attack_type}: {count}/{full} ({count / TARGET:.1%})")

print("\nSuite × attack type:")
for suite in sorted(suite_counts):
    for attack_type in sorted(attack_counts):
        count = sum(
            1
            for key, _ in selected
            if key[0] == suite and key[3] == attack_type
        )
        if count:
            print(f"  {suite} / {attack_type}: {count}")
