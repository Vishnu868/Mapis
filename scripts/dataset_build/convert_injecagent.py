import json
import os

input_file = "InjecAgent/data/test_cases_ds_base.json"
output_dir = "data/mapis_multihop"
output_file = os.path.join(output_dir, "injecagent_ds_base_sessions.jsonl")
summary_file = os.path.join(output_dir, "dataset_summary.json")

def convert_dataset():
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs("data/external/injecagent/", exist_ok=True)

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading input file: {e}")
        return

    sessions = []
    skipped = []
    
    summary = {
        "number_of_source_cases": len(data),
        "number_of_converted_sessions": 0,
        "number_containing_S1": 0,
        "number_containing_S2": 0,
        "number_by_attack_category": {},
        "number_of_messages_or_hops": 0,
        "exact_source_files": [input_file],
        "skipped_records": [],
        "limitations": [
            "Source dataset has no native 'session_id', using index instead.",
            "Hop 3 (Attacker Instruction) is the injected instruction intent, not an actual tool call JSON.",
            "Labels do not imply ground truth for MAPIS (ALLOW/WARN/BLOCK) but simply indicate it is an attack scenario."
        ]
    }

    for idx, case in enumerate(data):
        try:
            # Check for required fields
            if "User Instruction" not in case or "Tool Response" not in case or "Attacker Instruction" not in case:
                reason = "Missing required fields (User Instruction, Tool Response, or Attacker Instruction)"
                skipped.append({"index": idx, "reason": reason})
                summary["skipped_records"].append({"index": idx, "reason": reason})
                continue

            session_id = f"injecagent_ds_base_{idx:04d}"
            attack_category = case.get("Attack Type", "Unknown")

            messages = [
                {
                    "hop": 1,
                    "source": "user_context (DERIVED)",
                    "target": "agent (DERIVED)",
                    "content": case["User Instruction"],
                    "source_field": "User Instruction"
                },
                {
                    "hop": 2,
                    "source": "tool_response (DERIVED)",
                    "target": "agent (DERIVED)",
                    "content": case["Tool Response"],
                    "source_field": "Tool Response"
                },
                {
                    "hop": 3,
                    "source": "attacker_instruction (DERIVED)",
                    "target": "agent_action (DERIVED)",
                    "content": case["Attacker Instruction"],
                    "source_field": "Attacker Instruction"
                }
            ]

            session = {
                "session_id": session_id,
                "source": "InjecAgent",
                "source_file": os.path.basename(input_file),
                "source_case_id": str(idx),
                "label": "attack",
                "attack_category": attack_category,
                "num_hops": len(messages),
                "messages": messages
            }
            
            sessions.append(session)

            summary["number_containing_S1"] += 1
            summary["number_containing_S2"] += 1
            summary["number_by_attack_category"][attack_category] = summary["number_by_attack_category"].get(attack_category, 0) + 1
            summary["number_of_messages_or_hops"] += len(messages)

        except Exception as e:
            skipped.append({"index": idx, "reason": str(e)})
            summary["skipped_records"].append({"index": idx, "reason": str(e)})

    summary["number_of_converted_sessions"] = len(sessions)

    with open(output_file, 'w', encoding='utf-8') as f:
        for session in sessions:
            f.write(json.dumps(session) + "\n")
            
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=4)

    print(f"Conversion complete.")
    print(f"Converted {len(sessions)} sessions.")
    print(f"Skipped {len(skipped)} records.")
    
if __name__ == "__main__":
    convert_dataset()
