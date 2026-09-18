import json

path = "data/mapis_bench/mapis_bench_v1.jsonl"

with open(path, encoding="utf-8") as f:
    for line in f:
        r = json.loads(line)

        if r["sample_id"] == "agentdojo_0002":
            print("SAMPLE:", r["sample_id"])
            print("SOURCE LABEL:", r["source_label"])
            print("MAPIS CLASS:", r["mapis_attack_class"])
            print()

            for m in r["messages"]:
                content = m.get("content")

                if isinstance(content, str) and content:
                    print(f"--- HOP {m['hop']} | {m['role']} ---")
                    print(content)
                    print()

            break
