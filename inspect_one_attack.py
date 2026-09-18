import json

path = "data/mapis_bench/mapis_bench_v1.jsonl"

with open(path, encoding="utf-8") as f:
    for line in f:
        r = json.loads(line)

        if r["split"] == "test" and r["is_attack"]:
            print("SAMPLE:", r["sample_id"])
            print("SOURCE:", r["source_dataset"])
            print("CLASS:", r["mapis_attack_class"])
            print("MESSAGES:", len(r["messages"]))
            print()

            for m in r["messages"]:
                content = m.get("content")
                if content is None:
                    content = "<NO TEXT CONTENT>"

                print(
                    f"HOP {m['hop']} | "
                    f"{m['role']} | "
                    f"{m['source']} -> {m['target']}"
                )
                print("CONTENT:", str(content)[:500])
                print("-" * 80)

            break
