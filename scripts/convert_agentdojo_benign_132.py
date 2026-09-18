from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
SELECTION_FILE = ROOT / "data" / "mapis_multihop" / "agentdojo_benign_selected_132_keys.json"
OUTPUT_FILE = ROOT / "data" / "mapis_multihop" / "agentdojo_benign_132_raw.jsonl"

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def convert_message(message, hop):
    role = message.get("role")

    if role == "system":
        source, target = "system", "agent"
    elif role == "user":
        source, target = "user", "agent"
    elif role == "assistant":
        source = "agent"
        target = "tool" if message.get("tool_calls") else "user"
    elif role == "tool":
        source, target = "tool", "agent"
    else:
        source, target = role, "agent"

    record = {
        "hop": hop,
        "role": role,
        "source": source,
        "target": target,
        "content": message.get("content"),
    }

    for key in ["tool_calls", "tool_call_id", "tool_call", "error"]:
        if key in message:
            record[key] = message[key]

    return record

def main():
    selection = load_json(SELECTION_FILE)
    records = []

    for index, selected in enumerate(selection["records"]):
        source_path = ROOT / "data" / "external" / "agentdojo" / "runs" / selected["source_path"]
        case = load_json(source_path)

        messages = case.get("messages", [])

        record = {
            "sample_id": f"agentdojo_benign_{index:04d}",
            "source_dataset": "AgentDojo",
            "source_file": "data/external/agentdojo/runs/" + selected["source_path"],
            "source_record_id": {
                "suite_name": case.get("suite_name"),
                "user_task_id": case.get("user_task_id"),
                "injection_task_id": case.get("injection_task_id"),
                "attack_type": case.get("attack_type"),
            },
            "provenance": {
                "original_dataset": "AgentDojo",
                "pipeline_name": case.get("pipeline_name"),
                "original_label": None,
                "original_security": case.get("security"),
                "original_utility": case.get("utility"),
                "conversion_type": "chronological_native_trajectory",
            },
            "split": None,
            "is_attack": False,
            "source_label": {
                "attack_type": None,
                "security": case.get("security"),
                "utility": case.get("utility"),
            },
            "mapis_attack_class": None,
            "representation_type": "session_multihop",
            "messages": [
                convert_message(message, hop)
                for hop, message in enumerate(messages, start=1)
            ],
            "conversion_notes": (
                "Native AgentDojo benign trajectory preserved chronologically. "
                "No synthetic messages or attacker actions were added."
            ),
        }

        records.append(record)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print("AgentDojo benign converter")
    print(f"Selected source trajectories: {len(selection['records'])}")
    print(f"Converted records: {len(records)}")
    print(f"Output: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
