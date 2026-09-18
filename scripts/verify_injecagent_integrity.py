import json

source_attack = "data/external/injecagent/data/test_cases_ds_base.json"
source_benign = "data/external/injecagent/data/user_cases.jsonl"
output = "data/mapis_bench/mapis_bench_v1_injecagent.jsonl"

with open(source_attack, encoding="utf-8") as f:
    attacks = json.load(f)

with open(source_benign, encoding="utf-8") as f:
    benign = [json.loads(x) for x in f if x.strip()]

with open(output, encoding="utf-8") as f:
    records = [json.loads(x) for x in f if x.strip()]

attack_records = [x for x in records if x["is_attack"]]
benign_records = [x for x in records if not x["is_attack"]]

checks = {}

checks["attack_count"] = len(attacks) == len(attack_records)
checks["benign_count"] = len(benign) == len(benign_records)

checks["unique_sample_ids"] = len(records) == len(set(x["sample_id"] for x in records))

checks["attack_hop3_exact"] = all(
    attack_records[i]["messages"][2]["content"] == attacks[i]["Attacker Instruction"]
    for i in range(len(attacks))
)

checks["attack_hop2_contains_hop3"] = all(
    attacks[i]["Attacker Instruction"] in attack_records[i]["messages"][1]["content"]
    for i in range(len(attacks))
)

checks["benign_user_instruction_exact"] = all(
    benign_records[i]["messages"][0]["content"] == benign[i]["User Instruction"]
    for i in range(len(benign))
)

checks["benign_placeholder_preserved"] = all(
    "<Attacker Instruction>" in benign_records[i]["messages"][1]["content"]
    for i in range(len(benign))
)

checks["benign_class_null"] = all(
    x["mapis_attack_class"] is None
    for x in benign_records
)

print("MAPIS-Bench InjecAgent integrity check")
for name, result in checks.items():
    print(f"{name}: {'PASS' if result else 'FAIL'}")

print()
print("Overall:", "PASS" if all(checks.values()) else "FAIL")
