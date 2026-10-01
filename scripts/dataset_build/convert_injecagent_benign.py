import json
import os

input_file = "InjecAgent/data/user_cases.jsonl"
output_dir = "data/mapis_multihop"
output_file = os.path.join(output_dir, "injecagent_benign_sessions.jsonl")
summary_file = os.path.join(output_dir, "benign_dataset_summary.json")

def convert_benign():
    os.makedirs(output_dir, exist_ok=True)
    
    sessions = []
    skipped = []
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading {input_file}: {e}")
        return
        
    for idx, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            case = json.loads(line)
            
            # The tool response template contains the '<Attacker Instruction>' placeholder.
            # By replacing it with an empty string, we get the legitimate, benign base response.
            benign_tool_response = case["Tool Response Template"].replace("<Attacker Instruction>", "")
            
            # Create a 2-hop benign session
            messages = [
                {
                    "hop": 1,
                    "source": "user_context (ORIGINAL)",
                    "target": "agent (DERIVED)",
                    "content": case["User Instruction"],
                    "source_field": "User Instruction"
                },
                {
                    "hop": 2,
                    "source": "tool_response (CLEANED)",
                    "target": "agent (DERIVED)",
                    "content": benign_tool_response,
                    "source_field": "Tool Response Template"
                }
            ]
            
            session = {
                "session_id": f"injecagent_benign_{idx:04d}",
                "source": "InjecAgent",
                "source_file": "user_cases.jsonl",
                "source_case_id": str(idx),
                "label": "benign",
                "attack_category": None,
                "num_hops": len(messages),
                "messages": messages
            }
            sessions.append(session)
            
        except Exception as e:
            skipped.append({"index": idx, "reason": str(e)})
            
    summary = {
        "number_of_source_cases": len(lines),
        "number_of_converted_sessions": len(sessions),
        "number_of_messages_or_hops": sum(s["num_hops"] for s in sessions),
        "exact_source_files": [input_file],
        "exact_fields_used": ["User Instruction", "Tool Response Template"],
        "skipped_records": skipped,
        "genuinely_supported": True,
        "limitations": [
            "InjecAgent only provides 17 unique User Cases (benign scenarios).",
            "The dataset does not contain a benign Hop 3 (Agent Response to User) because it only focuses on evaluating the attack vector.",
            "Therefore, benign sessions are honestly limited to 2 hops (User -> Tool Response).",
            "The malicious '<Attacker Instruction>' placeholder was cleanly replaced with an empty string in the Tool Response Template to derive the explicitly supported benign S2 payload."
        ]
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for s in sessions:
            f.write(json.dumps(s) + "\n")
            
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=4)
        
    print(f"Created {len(sessions)} benign sessions.")
    print(f"Skipped {len(skipped)} records.")

if __name__ == '__main__':
    convert_benign()
