import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

inputs = [
    ROOT / "data" / "mapis_multihop" / "agentdojo_1000_raw.jsonl",
    ROOT / "data" / "mapis_multihop" / "agentdojo_benign_132.jsonl",
    ROOT / "data" / "mapis_bench" / "mapis_bench_v1_injecagent.jsonl",
]

output = ROOT / "data" / "mapis_bench" / "mapis_bench_v1.jsonl"

records = []

for path in inputs:
    with open(path, encoding="utf-8") as f:
        records.extend(json.loads(line) for line in f if line.strip())

ids = [r["sample_id"] for r in records]

print("Input files:", len(inputs))
print("Total records:", len(records))
print("Unique sample IDs:", len(set(ids)))
print("Duplicate IDs:", len(ids) - len(set(ids)))

with open(output, "w", encoding="utf-8") as f:
    for record in records:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

print("Output:", output)
