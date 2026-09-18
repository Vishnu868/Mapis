import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, ".")

from backend.core.trust_scorer import TrustScorer
from backend.models.schemas import TrustDecision


DATASET = Path("data/mapis_bench/mapis_bench_v1.jsonl")
OUTPUT_DIR = Path("results/mapis_bench_v1")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_dataset():
    records = []
    with DATASET.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def is_detected(decision):
    return decision in {
        TrustDecision.WARN,
        TrustDecision.BLOCK,
    }


def evaluate():
    records = [
        r for r in load_dataset()
        if r["split"] == "test"
    ]

    print(f"Test sessions: {len(records)}")
    print(f"Attack sessions: {sum(r['is_attack'] for r in records)}")
    print(f"Benign sessions: {sum(not r['is_attack'] for r in records)}")

    scorer = TrustScorer()

    session_results = []
    class_stats = defaultdict(lambda: {"total": 0, "detected": 0})
    hop_stats = defaultdict(lambda: {"total": 0, "detected": 0})

    tp = fn = tn = fp = 0

    for record in records:
        session_id = f"bench_{record['sample_id']}"

        attack_detected = False
        events = []

        for message in record["messages"]:
            content = message.get("content")

            if not isinstance(content, str) or not content.strip():
                continue

            result = scorer.score_message(
                session_id=session_id,
                source_agent=message["source"],
                target_agent=message["target"],
                message=content,
            )

            detected = is_detected(result.decision)

            events.append({
                "hop": message["hop"],
                "source": message["source"],
                "target": message["target"],
                "decision": result.decision.value,
                "score": result.final_score,
                "pattern_hits": result.pattern_hits,
            })

            if detected:
                attack_detected = True

            if record["is_attack"]:
                hop_stats[message["hop"]]["total"] += 1
                if detected:
                    hop_stats[message["hop"]]["detected"] += 1

        if record["is_attack"]:
            attack_class = record["mapis_attack_class"]

            if attack_class is not None:
                class_stats[attack_class]["total"] += 1
                if attack_detected:
                    class_stats[attack_class]["detected"] += 1

            if attack_detected:
                tp += 1
            else:
                fn += 1

        else:
            if attack_detected:
                fp += 1
            else:
                tn += 1

        session_results.append({
            "sample_id": record["sample_id"],
            "is_attack": record["is_attack"],
            "attack_class": record["mapis_attack_class"],
            "detected": attack_detected,
            "events": events,
        })

        scorer.clear_session(session_id)

    total_attack = tp + fn
    total_benign = tn + fp

    recall = tp / total_attack if total_attack else 0
    precision = tp / (tp + fp) if (tp + fp) else 0
    fpr = fp / total_benign if total_benign else 0
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0
    )

    summary = {
        "dataset": "MAPIS-Bench v1",
        "split": "test",
        "sessions": len(records),
        "attack_sessions": total_attack,
        "benign_sessions": total_benign,
        "true_positives": tp,
        "false_negatives": fn,
        "true_negatives": tn,
        "false_positives": fp,
        "recall": recall,
        "precision": precision,
        "false_positive_rate": fpr,
        "f1": f1,
        "per_class": {},
        "per_hop": {},
    }

    for attack_class, stats in sorted(class_stats.items()):
        summary["per_class"][attack_class] = {
            "total": stats["total"],
            "detected": stats["detected"],
            "recall": (
                stats["detected"] / stats["total"]
                if stats["total"]
                else 0
            ),
        }

    for hop, stats in sorted(hop_stats.items()):
        summary["per_hop"][str(hop)] = {
            "total": stats["total"],
            "detected": stats["detected"],
            "detection_rate": (
                stats["detected"] / stats["total"]
                if stats["total"]
                else 0
            ),
        }

    with (OUTPUT_DIR / "summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    with (OUTPUT_DIR / "session_results.jsonl").open("w", encoding="utf-8") as f:
        for result in session_results:
            f.write(json.dumps(result) + "\n")

    print("\nMAPIS-Bench v1 — Current Heuristic Baseline")
    print("--------------------------------------------")
    print(f"TP:        {tp}")
    print(f"FN:        {fn}")
    print(f"TN:        {tn}")
    print(f"FP:        {fp}")
    print(f"Recall:    {recall:.2%}")
    print(f"Precision: {precision:.2%}")
    print(f"FPR:       {fpr:.2%}")
    print(f"F1:        {f1:.4f}")

    print("\nPer attack class:")
    for attack_class, stats in sorted(class_stats.items()):
        rate = stats["detected"] / stats["total"]
        print(
            f"  {attack_class:25s} "
            f"{stats['detected']:3d}/{stats['total']:3d} "
            f"({rate:.2%})"
        )

    print(f"\nResults saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    evaluate()
