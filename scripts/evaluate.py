"""
MAPIS Evaluation Script
========================
Measures detection accuracy (attack recall) and false positive rate
across the full dataset. Use this to generate metrics for your research paper.

Usage:
    python scripts/evaluate.py
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from rich.console import Console
from rich.table import Table
from rich import box

from backend.core.trust_scorer import TrustScorer
from backend.models.schemas import TrustDecision

console = Console()


def load_samples(path: str) -> list:
    with open(path) as f:
        return json.load(f)


def evaluate():
    scorer = TrustScorer()

    attacks = load_samples("data/attack_samples/attacks.json")
    benigns = load_samples("data/benign_samples/benign.json")

    console.print("\n[bold cyan]MAPIS Evaluation Report[/bold cyan]\n")

    # ── Attack Detection ───────────────────────────────────────────────────
    atk_results = {"TP": 0, "FN": 0, "details": []}

    for i, sample in enumerate(attacks):
        session_id = f"eval_atk_{i}"
        result = scorer.score_message(
            session_id, "eval_source", "eval_target", sample["message"]
        )

        caught = result.decision in [TrustDecision.WARN, TrustDecision.BLOCK]
        expected_caught = sample["expected_decision"] in ["WARN", "BLOCK"]

        if expected_caught:
            if caught:
                atk_results["TP"] += 1
            else:
                atk_results["FN"] += 1
            atk_results["details"].append({
                "id": sample["id"],
                "category": sample["category"],
                "expected": sample["expected_decision"],
                "got": result.decision,
                "score": result.final_score,
                "correct": caught
            })

    # ── Benign False Positive Rate ─────────────────────────────────────────
    ben_results = {"TN": 0, "FP": 0, "details": []}

    for i, sample in enumerate(benigns):
        session_id = f"eval_ben_{i}"
        result = scorer.score_message(
            session_id, "eval_source", "eval_target", sample["message"]
        )

        is_fp = result.decision != TrustDecision.ALLOW
        if is_fp:
            ben_results["FP"] += 1
        else:
            ben_results["TN"] += 1

        ben_results["details"].append({
            "id": sample["id"],
            "expected": "ALLOW",
            "got": result.decision,
            "score": result.final_score,
            "correct": not is_fp
        })

    # ── Print Results ──────────────────────────────────────────────────────
    tp = atk_results["TP"]
    fn = atk_results["FN"]
    tn = ben_results["TN"]
    fp = ben_results["FP"]

    total_attacks = tp + fn
    total_benign  = tn + fp

    recall    = tp / total_attacks if total_attacks > 0 else 0
    precision = tp / (tp + fp)    if (tp + fp) > 0    else 0
    fpr       = fp / total_benign  if total_benign > 0 else 0
    f1        = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0

    table = Table(box=box.ROUNDED, header_style="bold white")
    table.add_column("Metric",       width=35)
    table.add_column("Value",        width=15, justify="right")
    table.add_column("Interpretation", width=30)

    table.add_row("True Positives (Attacks Caught)",   str(tp),             f"out of {total_attacks} attacks")
    table.add_row("False Negatives (Attacks Missed)",  str(fn),             "lower is better")
    table.add_row("True Negatives (Benign Allowed)",   str(tn),             f"out of {total_benign} benign")
    table.add_row("False Positives (Benign Blocked)",  str(fp),             "lower is better")
    table.add_row("─" * 34,                            "─" * 14,            "─" * 29)
    table.add_row("Detection Rate (Recall)",           f"[green]{recall:.1%}[/green]",   "% attacks detected")
    table.add_row("Precision",                         f"[green]{precision:.1%}[/green]", "% of blocks that were real attacks")
    table.add_row("False Positive Rate",               f"[yellow]{fpr:.1%}[/yellow]",    "% benign messages blocked")
    table.add_row("F1 Score",                          f"[cyan]{f1:.3f}[/cyan]",         "harmonic mean of P and R")

    console.print(table)

    # ── Per-Category Breakdown ─────────────────────────────────────────────
    console.print("\n[bold]Per-Category Results:[/bold]\n")

    cat_table = Table(box=box.SIMPLE, header_style="bold white")
    cat_table.add_column("Category",    width=28)
    cat_table.add_column("Expected",    width=10)
    cat_table.add_column("Got",         width=10)
    cat_table.add_column("Score",       width=8, justify="right")
    cat_table.add_column("Result",      width=10)

    for d in atk_results["details"]:
        color = "green" if d["correct"] else "red"
        cat_table.add_row(
            d["category"],
            d["expected"],
            d["got"],
            f"{d['score']:.3f}",
            f"[{color}]{'✅ CAUGHT' if d['correct'] else '❌ MISSED'}[/{color}]"
        )

    console.print(cat_table)

    console.print(f"\n[bold]Summary:[/bold] "
                  f"MAPIS detected [green]{tp}/{total_attacks}[/green] attacks "
                  f"with [yellow]{fp}[/yellow] false positives "
                  f"(F1: [cyan]{f1:.3f}[/cyan])\n")


if __name__ == "__main__":
    evaluate()
