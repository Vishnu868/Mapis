import json

p = "data/mapis_bench/mapis_bench_v1_injecagent.jsonl"

with open(p, encoding="utf-8") as f:
    records = [json.loads(x) for x in f if x.strip()]

for x in records:
    if x["mapis_attack_class"] == "code_tool_manipulation":
        print(x["sample_id"])
        print(x["messages"][2]["content"])
        print("-" * 80)
