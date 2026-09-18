import json
from backend.core.trust_scorer import TrustScorer

path = "data/mapis_bench/mapis_bench_v1.jsonl"

with open(path, encoding="utf-8") as f:
    for line in f:
        r = json.loads(line)
        if r["sample_id"] == "agentdojo_0002":
            scorer = TrustScorer()

            for m in r["messages"]:
                content = m.get("content")

                if not isinstance(content, str) or not content.strip():
                    continue

                result = scorer.score_message(
                    session_id=r["sample_id"],
                    source_agent=m["source"],
                    target_agent=m["target"],
                    message=content,
                    metadata={"hop": m["hop"]}
                )

                print(
                    f"HOP {m['hop']} | "
                    f"{m['role']} | "
                    f"{m['source']} -> {m['target']}"
                )
                print(f"Decision: {result.decision}")
                print(f"Raw score: {result.raw_score:.4f}")
                print(f"Final score: {result.final_score:.4f}")
                print(f"Pattern hits: {result.pattern_hits}")
                print(f"Drift hits: {result.drift_hits}")
                print(f"Explanation: {result.explanation}")
                print("-" * 80)

            break
