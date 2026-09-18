from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
SELECTION_FILE = ROOT / "data" / "mapis_multihop" / "agentdojo_selected_1000_keys.json"
OUTPUT_FILE = ROOT / "data" / "mapis_multihop" / "agentdojo_1000_raw.jsonl"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def convert_message(message, hop):
    role = message.get("role")

    record = {
        "hop": hop,
        "role": role,
        "content": message.get("content"),
    }

    if "tool_calls" in message:
        record["tool_calls"] = message.get("tool_calls")

    if "tool_call_id" in message:
        record["tool_call_id"] = message.get("tool_call_id")

    if "tool_call" in message:
        record["tool_call"] = message.get("tool_call")

    if "error" in message:
        record["error"] = message.get("error")

    return record


def main():
    selection = load_json(SELECTION_FILE)

    records = []

    for index, selected in enumerate(selection["records"]):
        source_path = ROOT / selected["source_path"]
        case = load_json(source_path)

        messages = case.get("messages", [])

        converted_messages = [
            convert_message(message, hop)
            for hop, message in enumerate(messages, start=1)
        ]

        record = {
            "sample_id": f"agentdojo_{index:04d}",
            "source_dataset": "AgentDojo",
            "source_file": selected["source_path"],
            "source_record_id": {
                "suite_name": case.get("suite_name"),
                "user_task_id": case.get("user_task_id"),
                "injection_task_id": case.get("injection_task_id"),
                "attack_type": case.get("attack_type"),
            },
            "provenance": {
                "original_dataset": "AgentDojo",
                "pipeline_name": case.get("pipeline_name"),
                "original_security": case.get("security"),
                "original_utility": case.get("utility"),
                "conversion_type": "chronological_native_trajectory",
            },
            "split": None,
            "is_attack": True,
            "source_label": {
                "attack_type": case.get("attack_type"),
            },
            "mapis_attack_class": None,
            "representation_type": "session_multihop",
            "messages": converted_messages,
            "conversion_notes": (
                "Native AgentDojo trajectory preserved chronologically. "
                "No synthetic messages or attacker actions were added. "
                "Injection content remains inside its original tool response."
            ),
        }

        records.append(record)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print("AgentDojo converter")
    print(f"Selected source trajectories: {len(selection['records'])}")
    print(f"Converted records: {len(records)}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
