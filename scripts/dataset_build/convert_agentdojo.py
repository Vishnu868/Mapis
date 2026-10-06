import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTDOJO_DIR = ROOT / "data" / "external" / "agentdojo"
BENCH_DIR = ROOT / "data" / "mapis_bench"

MODEL = "claude-3-5-sonnet-20240620"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def has_embedded_injection(messages):
    return any(
        m.get("role") == "tool"
        and isinstance(m.get("content"), str)
        and "<INFORMATION>" in m["content"]
        for m in messages
    )


def find_injection_tool_index(messages):
    for i, message in enumerate(messages):
        if (
            message.get("role") == "tool"
            and isinstance(message.get("content"), str)
            and "<INFORMATION>" in message["content"]
        ):
            return i
    return None


def main():
    root = AGENTDOJO_DIR / "runs" / MODEL

    files = list(root.rglob("injection_task_*.json"))

    candidates = []

    for path in files:
        record = load_json(path)
        messages = record.get("messages", [])

        if not has_embedded_injection(messages):
            continue

        injection_index = find_injection_tool_index(messages)

        candidates.append(
            {
                "path": str(path.relative_to(ROOT)),
                "suite": record.get("suite_name"),
                "user_task_id": record.get("user_task_id"),
                "injection_task_id": record.get("injection_task_id"),
                "attack_type": record.get("attack_type"),
                "injection_index": injection_index,
                "message_count": len(messages),
            }
        )

    print("AgentDojo converter")
    print(f"Total injection-task files: {len(files)}")
    print(f"Native embedded candidates: {len(candidates)}")

    if candidates:
        print("Example:")
        print(json.dumps(candidates[0], indent=2))


if __name__ == "__main__":
    main()
