import json
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
BENCH_DIR = ROOT / "data" / "mapis_bench"
SCHEMA_FILE = BENCH_DIR / "dataset_schema.json"
TAXONOMY_FILE = BENCH_DIR / "taxonomy_proposal.json"
INJECAGENT_DIR = ROOT / "data" / "external" / "injecagent"


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def load_jsonl(path):
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def split_for_group(group_index):
    if group_index < 12:
        return "train"
    if group_index < 14:
        return "validation"
    return "test"


def convert_injecagent_attack(case, index):
    messages = [
        {
            "hop": 1,
            "role": "user",
            "source": "user",
            "target": "agent",
            "content": case["User Instruction"]
        },
        {
            "hop": 2,
            "role": "tool_response",
            "source": "user_tool",
            "target": "agent",
            "content": case["Tool Response"],
            "tool_name": case["User Tool"],
            "tool_response": case["Tool Response"]
        },
        {
            "hop": 3,
            "role": "attacker_instruction",
            "source": "attacker",
            "target": "agent",
            "content": case["Attacker Instruction"]
        }
    ]

    return {
        "sample_id": f"injecagent_ds_{index:04d}",
        "source_dataset": "InjecAgent",
        "source_file": "data/test_cases_ds_base.json",
        "source_record_id": str(index),
        "provenance": {
            "original_dataset": "InjecAgent",
            "original_label": case["Attack Type"],
            "conversion_type": "derived"
        },
        "split": split_for_group(index % 17),
        "is_attack": True,
        "source_label": {
            "attack_type": case["Attack Type"]
        },
        "mapis_attack_class": None,
        "representation_type": "session_multihop",
        "messages": messages,
        "conversion_notes": "Source case converted into a chronological multi-hop representation. Hop 2 is the source Tool Response containing the injected attacker instruction. Hop 3 represents the attacker instruction extracted from the source case. Hop 3 is not an actual attacker tool-call JSON."
    }


def convert_injecagent_benign(case, index, group_index):
    messages = [
        {
            "hop": 1,
            "role": "user",
            "source": "user",
            "target": "agent",
            "content": case["User Instruction"]
        },
        {
            "hop": 2,
            "role": "tool_response_template",
            "source": "user_tool",
            "target": "agent",
            "content": case["Tool Response Template"],
            "tool_name": case["User Tool"],
            "tool_response": case["Tool Response Template"]
        }
    ]

    return {
        "sample_id": f"injecagent_benign_{index:04d}",
        "source_dataset": "InjecAgent",
        "source_file": "data/user_cases.jsonl",
        "source_record_id": str(index),
        "provenance": {
            "original_dataset": "InjecAgent",
            "original_label": case.get("Level"),
            "conversion_type": "cleaned"
        },
        "split": split_for_group(group_index),
        "is_attack": False,
        "source_label": {
            "level": case.get("Level")
        },
        "mapis_attack_class": None,
        "representation_type": "session_multihop",
        "messages": messages,
        "conversion_notes": "Benign source case converted into a two-hop representation. The source Tool Response Template contains the literal <Attacker Instruction> placeholder; this is preserved as source content and is not treated as an attack instruction."
    }


def main():
    schema = load_json(SCHEMA_FILE)
    taxonomy = load_json(TAXONOMY_FILE)

    attack_file = INJECAGENT_DIR / "data" / "test_cases_ds_base.json"
    benign_file = INJECAGENT_DIR / "data" / "user_cases.jsonl"

    attacks = load_json(attack_file)
    benign = load_jsonl(benign_file)

    validator = jsonschema.Draft202012Validator(schema)

    attack_context_group = {}
    for index, case in enumerate(attacks):
        attack_context_group.setdefault(case["User Instruction"], index % 17)

    records = [
        convert_injecagent_attack(case, index)
        for index, case in enumerate(attacks)
    ]

    for index, case in enumerate(benign):
        group_index = attack_context_group[case["User Instruction"]]
        records.append(convert_injecagent_benign(case, index, group_index))

    errors = []
    for record in records:
        errors.extend(validator.iter_errors(record))

    print("MAPIS-Bench builder")
    print(f"InjecAgent attack cases: {len(attacks)}")
    print(f"InjecAgent benign cases: {len(benign)}")
    print(f"Total converted records: {len(records)}")
    print(f"Attack records: {sum(r['is_attack'] for r in records)}")
    print(f"Benign records: {sum(not r['is_attack'] for r in records)}")
    print(f"Validation errors: {len(errors)}")
    print(f"Taxonomy status: {taxonomy['status']}")
    output_file = BENCH_DIR / "mapis_bench_v1_injecagent.jsonl"
    with open(output_file, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Output: {output_file}")


if __name__ == "__main__":
    main()
