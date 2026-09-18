import json
from pathlib import Path
from collections import Counter

root = Path("data/external/agentdojo/runs")

files = list(root.rglob("injection_task_*.json"))

stats = Counter()

for p in files:
    try:
        x = json.load(open(p, encoding="utf-8"))
    except Exception:
        stats["invalid_json"] += 1
        continue

    messages = x.get("messages", [])

    stats["files"] += 1

    if len(messages) >= 3:
        stats["messages_ge_3"] += 1

    has_tool = any(m.get("role") == "tool" for m in messages)
    has_assistant_tool_call = any(
        m.get("role") == "assistant" and m.get("tool_calls")
        for m in messages
    )

    if has_tool:
        stats["has_tool_response"] += 1

    if has_assistant_tool_call:
        stats["has_assistant_tool_call"] += 1

    if has_tool and has_assistant_tool_call:
        stats["multi_hop_candidate"] += 1

    injection_payload = x.get("injections", {})
    if isinstance(injection_payload, dict) and any(
        isinstance(v, str) and v.strip()
        for v in injection_payload.values()
    ):
        stats["has_injection_payload"] += 1

    embedded = any(
        isinstance(m.get("content"), str)
        and "<INFORMATION>" in m["content"]
        for m in messages
    )

    if embedded:
        stats["injection_embedded_in_message"] += 1

print("AgentDojo trajectory measurement")
for k, v in stats.items():
    print(f"{k}: {v}")
