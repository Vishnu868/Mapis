import json
from pathlib import Path

root = Path("data/external/agentdojo/runs")

shown = 0

for p in root.rglob("injection_task_*.json"):
    x = json.load(open(p, encoding="utf-8"))
    messages = x.get("messages", [])

    embedded = any(
        isinstance(m.get("content"), str)
        and "<INFORMATION>" in m["content"]
        for m in messages
    )

    if not embedded and len(messages) >= 3:
        print("=" * 100)
        print("FILE:", p)
        print("ATTACK TYPE:", x.get("attack_type"))
        print("INJECTIONS:", json.dumps(x.get("injections"), ensure_ascii=False))
        print("MESSAGES:")
        for i, m in enumerate(messages):
            print(f"[{i}] ROLE={m.get('role')}")
            print("CONTENT:", str(m.get("content"))[:1000])
            if m.get("tool_calls"):
                print("TOOL_CALLS:", json.dumps(m["tool_calls"], ensure_ascii=False))
        shown += 1

        if shown >= 3:
            break

print()
print("Examples shown:", shown)
