import json
import csv
import time
import os
from pathlib import Path
from collections import defaultdict

import sys
sys.path.append(str(Path(__file__).parent.parent))

from backend.core.trust_scorer import TrustScorer
from backend.models.schemas import TrustDecision

def main():
    attack_file = "data/mapis_multihop/injecagent_ds_base_sessions.jsonl"
    benign_file = "data/mapis_multihop/injecagent_benign_sessions.jsonl"
    
    attack_sessions = []
    with open(attack_file, 'r') as f:
        for line in f:
            attack_sessions.append(json.loads(line))
            
    benign_sessions = []
    with open(benign_file, 'r') as f:
        for line in f:
            benign_sessions.append(json.loads(line))

    out_dir = Path("results/injecagent")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    scorer = TrustScorer()
    
    def evaluate(sessions, mode):
        t0 = time.perf_counter()
        total_msgs = 0
        m_res = []
        s_res = []
        
        for sess in sessions:
            sess_id = sess["session_id"]
            # Always clear session at the beginning of a session
            scorer.clear_session(sess_id)
            
            sess_detected = False
            first_hop = None
            
            for msg in sess["messages"]:
                if mode == "stateless":
                    # Clear history before every message so it's treated independently
                    scorer.clear_session(sess_id)
                    
                score_obj = scorer.score_message(
                    session_id=sess_id,
                    source_agent=msg["source"],
                    target_agent=msg["target"],
                    message=msg["content"]
                )
                
                # Decision mapping: ALLOW is safe. WARN and BLOCK are suspicious/security decisions.
                detected = score_obj.decision in [TrustDecision.WARN, TrustDecision.BLOCK]
                
                m_res.append({
                    "session_id": sess_id,
                    "source_case_id": sess["source_case_id"],
                    "attack_category": sess.get("attack_category", "Benign"),
                    "label": sess["label"],
                    "hop": msg["hop"],
                    "mode": mode,
                    "score": score_obj.final_score,
                    "decision": score_obj.decision.value,
                    "detected": detected
                })
                
                if detected and not sess_detected:
                    sess_detected = True
                    first_hop = msg["hop"]
                    
                total_msgs += 1
                
            s_res.append({
                "session_id": sess_id,
                "label": sess["label"],
                "attack_category": sess.get("attack_category", "Benign"),
                "mode": mode,
                "num_hops": sess["num_hops"],
                "detected": sess_detected,
                "first_detected_hop": first_hop
            })
            
        t1 = time.perf_counter()
        return m_res, s_res, total_msgs, (t1 - t0)

    # Evaluate
    print("Evaluating Stateful Attack...")
    att_m_sf, att_s_sf, att_mc_sf, att_t_sf = evaluate(attack_sessions, "stateful")
    print("Evaluating Stateless Attack...")
    att_m_sl, att_s_sl, att_mc_sl, att_t_sl = evaluate(attack_sessions, "stateless")
    
    print("Evaluating Stateful Benign...")
    ben_m_sf, ben_s_sf, ben_mc_sf, ben_t_sf = evaluate(benign_sessions, "stateful")
    print("Evaluating Stateless Benign...")
    ben_m_sl, ben_s_sl, ben_mc_sl, ben_t_sl = evaluate(benign_sessions, "stateless")
    
    all_m = att_m_sf + att_m_sl + ben_m_sf + ben_m_sl
    all_s = att_s_sf + att_s_sl + ben_s_sf + ben_s_sl
    
    # Write Message Results
    m_keys = ["session_id", "source_case_id", "attack_category", "label", "hop", "mode", "score", "decision", "detected"]
    with open(out_dir / "message_level_results.csv", 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=m_keys)
        writer.writeheader()
        writer.writerows(all_m)
        
    # Write Session Results
    s_keys = ["session_id", "label", "attack_category", "mode", "num_hops", "detected", "first_detected_hop"]
    with open(out_dir / "session_level_results.csv", 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=s_keys)
        writer.writeheader()
        writer.writerows(all_s)
        
    # Calculate Experiment 2 metrics (Session level, Stateful)
    # TP: attack detected
    # TN: benign NOT detected
    # FP: benign detected
    # FN: attack NOT detected
    def calc_metrics(sess_res):
        TP = sum(1 for s in sess_res if s["label"] == "attack" and s["detected"])
        TN = sum(1 for s in sess_res if s["label"] == "benign" and not s["detected"])
        FP = sum(1 for s in sess_res if s["label"] == "benign" and s["detected"])
        FN = sum(1 for s in sess_res if s["label"] == "attack" and not s["detected"])
        
        acc = (TP + TN) / (TP + TN + FP + FN) if (TP + TN + FP + FN) > 0 else 0.0
        prec = TP / (TP + FP) if (TP + FP) > 0 else 0.0
        rec = TP / (TP + FN) if (TP + FN) > 0 else 0.0
        f1 = 2 * (prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        fpr = FP / (FP + TN) if (FP + TN) > 0 else 0.0
        spec = TN / (TN + FP) if (TN + FP) > 0 else 0.0
        
        return {"TP": TP, "TN": TN, "FP": FP, "FN": FN, "accuracy": acc, "precision": prec, "recall": rec, "f1": f1, "fpr": fpr, "specificity": spec}
        
    metrics_stateful = calc_metrics(att_s_sf + ben_s_sf)
    metrics_stateless = calc_metrics(att_s_sl + ben_s_sl)
    
    # Calculate Category and Hop metrics for Attack Stateful
    cat_stats = defaultdict(lambda: {"total": 0, "detected": 0})
    for s in att_s_sf:
        cat = s["attack_category"]
        cat_stats[cat]["total"] += 1
        if s["detected"]:
            cat_stats[cat]["detected"] += 1
            
    with open(out_dir / "category_results.csv", 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Category", "Total_Sessions", "Detected_Sessions", "Detection_Rate"])
        for cat, stats in cat_stats.items():
            writer.writerow([cat, stats["total"], stats["detected"], stats["detected"]/stats["total"]])
            
    hop_stats = defaultdict(lambda: {"total": 0, "detected": 0})
    for m in att_m_sf:
        h = m["hop"]
        hop_stats[h]["total"] += 1
        if m["detected"]:
            hop_stats[h]["detected"] += 1
            
    with open(out_dir / "hop_results.csv", 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Hop", "Total_Messages", "Detected_Messages", "Detection_Rate"])
        for h, stats in sorted(hop_stats.items()):
            writer.writerow([h, stats["total"], stats["detected"], stats["detected"]/stats["total"]])
            
    # Latency
    tot_msgs = att_mc_sf + att_mc_sl + ben_mc_sf + ben_mc_sl
    tot_time = att_t_sf + att_t_sl + ben_t_sf + ben_t_sl
    lat_res = {
        "total_messages_processed": tot_msgs,
        "total_evaluation_time_seconds": tot_time,
        "average_time_per_message_seconds": tot_time / tot_msgs if tot_msgs > 0 else 0,
        "average_time_per_session_seconds": (att_t_sf + ben_t_sf) / (len(attack_sessions) + len(benign_sessions))
    }
    with open(out_dir / "latency_results.json", 'w') as f:
        json.dump(lat_res, f, indent=4)
        
    summary = {
        "stateful_session_metrics": metrics_stateful,
        "stateless_session_metrics": metrics_stateless,
        "stateful_vs_stateless_recall_diff": metrics_stateful["recall"] - metrics_stateless["recall"],
        "total_attack_sessions": len(attack_sessions),
        "total_benign_sessions": len(benign_sessions)
    }
    with open(out_dir / "evaluation_summary.json", 'w') as f:
        json.dump(summary, f, indent=4)
        
    # Markdown Report
    report = f"""# MAPIS Evaluation Report
    
## Experiment 1: Stateful vs Stateless
- Stateful Recall: {metrics_stateful['recall']:.2%}
- Stateless Recall: {metrics_stateless['recall']:.2%}
- The stateful memory mechanism improves detection recall by {(metrics_stateful['recall'] - metrics_stateless['recall'])*100:.2f} percentage points.

## Experiment 2: Attack + Benign Control
Session-level Metrics (Stateful):
- True Positives (Attack caught): {metrics_stateful['TP']}
- True Negatives (Benign allowed): {metrics_stateful['TN']}
- False Positives (Benign caught): {metrics_stateful['FP']}
- False Negatives (Attack allowed): {metrics_stateful['FN']}
- Accuracy: {metrics_stateful['accuracy']:.2%}
- Precision: {metrics_stateful['precision']:.2%}
- F1 Score: {metrics_stateful['f1']:.2%}
- False Positive Rate (FPR): {metrics_stateful['fpr']:.2%}

## Experiment 3: Latency
- Total Messages Processed: {lat_res['total_messages_processed']}
- Average Time per Message: {lat_res['average_time_per_message_seconds']*1000:.2f} ms
- Average Time per Session (Stateful): {lat_res['average_time_per_session_seconds']*1000:.2f} ms
"""
    with open(out_dir / "evaluation_report.md", 'w') as f:
        f.write(report)
        
    print("Evaluation Complete.")

if __name__ == "__main__":
    main()
