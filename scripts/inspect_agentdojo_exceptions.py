import json

rows = [
    json.loads(x)
    for x in open(
        "data/mapis_multihop/agentdojo_1000_raw.jsonl",
        encoding="utf-8"
    )
    if x.strip()
]

for r in rows:
    if r["sample_id"] not in {"agentdojo_0228", "agentdojo_0279"}:
        continue

    print("\n===" + r["sample_id"] + "===")
    print("Source:", r["source_file"])
    print("Messages:", len(r["messages"]))

    for i, m in enumerate(r["messages"]):
        content = str(m.get("content") or "").replace("\n", " ")
        print(
            i,
            m.get("role"),
            "tool_calls=" + str(bool(m.get("tool_calls"))),
            "content=" + content[:300]
        )
