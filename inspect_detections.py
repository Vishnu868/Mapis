import json

path = "results/mapis_bench_v1/session_results.jsonl"

count = 0

with open(path, encoding="utf-8") as f:
    for line in f:
        r = json.loads(line)

        if r["is_attack"] and r["detected"]:
            print("\n", r["sample_id"], "|", r["attack_class"])

            for e in r["events"]:
                if e["decision"] != "ALLOW":
                    print(
                        "  hop", e["hop"],
                        "|", e["source"], "->", e["target"],
                        "|", e["decision"],
                        "| score", e["score"],
                        "| hits", [
                            h["category"]
                            for h in e["pattern_hits"]
                        ]
                    )

            count += 1

            if count >= 10:
                break
