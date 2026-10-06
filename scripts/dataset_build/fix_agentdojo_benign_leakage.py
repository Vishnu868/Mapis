import json
from pathlib import Path
from collections import defaultdict, Counter

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "mapis_bench" / "mapis_bench_v1.jsonl"
OUTPUT = ROOT / "data" / "mapis_bench" / "mapis_bench_v1.jsonl"

with open(INPUT, encoding="utf-8") as f:
    records = [json.loads(line) for line in f if line.strip()]

agentdojo_groups = defaultdict(set)

for r in records:
    if r["source_dataset"] != "AgentDojo":
        continue

    rid = r["source_record_id"]
    key = (rid.get("suite_name"), rid.get("user_task_id"))

    if r["is_attack"]:
        agentdojo_groups[key].add(r["split"])

changes = []

for r in records:
    if r["source_dataset"] != "AgentDojo" or r["is_attack"]:
        continue

    rid = r["source_record_id"]
    key = (rid.get("suite_name"), rid.get("user_task_id"))

    attack_splits = agentdojo_groups.get(key, set())

    if len(attack_splits) == 1:
        new_split = next(iter(attack_splits))

        if r["split"] != new_split:
            changes.append(
                (
                    r["sample_id"],
                    key,
                    r["split"],
                    new_split,
                )
            )
            r["split"] = new_split

print("Benign split changes:", len(changes))

for sample_id, key, old, new in changes:
    print(sample_id, key, old, "->", new)

with open(OUTPUT, "w", encoding="utf-8") as f:
    for r in records:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

print()
print("Total records:", len(records))
print("New split counts:", Counter(r["split"] for r in records))
print("Output:", OUTPUT)
