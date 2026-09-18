import json
from pathlib import Path
from collections import Counter

root = Path("data/external/agentdojo/runs")
stats = Counter()

for p in root.rglob("injection_task_*.json"):
    x = json.load(open(p, encoding="utf-8"))
    messages = x.get("messages", [])

    for i, m in enumerate(messages):
        if (
            m.get("role") == "tool"
            and isinstance(m.get("content"), str)
            and "<INFORMATION>" in m["content"]
        ):
            stats["injection_tool_messages"] += 1

            if i + 1 < len(messages):
                stats["has_next_message"] += 1
                if messages[i + 1].get("role") == "assistant":
                    stats["next_is_assistant"] += 1

            if m.get("tool_call"):
                stats["has_tool_call_metadata"] += 1

            break

print("Injection ? agent-action structure")
for k, v in stats.items():
    print(f"{k}: {v}")
