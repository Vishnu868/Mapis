"""Mean +/- std over training seeds: results/benchmark.json (seed 42) + results/seeds/benchmark_seed*.json -> results/seeds/summary.json."""

import json
import statistics
from pathlib import Path

files = [Path("results/benchmark.json"), *sorted(Path("results/seeds").glob("benchmark_seed*.json"))]
runs = [json.loads(f.read_text()) for f in files if f.exists()]
summary = {}
for system in ("mapis", "deberta-v3-small"):
    rows = [r[system] for r in runs if system in r]
    for scope in ("overall", "MAPIS-MultiHop", "RealHarm: InjecAgent direct harm", "RealHarm: ASB", "BIPIA (unseen dataset)",
                  "MAPIS-Adaptive (evasive attacker)", "MAPIS-Decomposed", "MAPIS-Bench v1"):
        vals = [(r["overall"] if scope == "overall" else r["by_set"].get(scope)) for r in rows]
        vals = [v for v in vals if v]
        if not vals:
            continue
        summary[f"{system} | {scope}"] = {
            m: {"mean": round(statistics.fmean(v[m] for v in vals), 4), "std": round(statistics.pstdev(v[m] for v in vals), 4)}
            for m in ("recall", "fpr", "accuracy", "f1")} | {"runs": len(vals)}
Path("results/seeds").mkdir(parents=True, exist_ok=True)
Path("results/seeds/summary.json").write_text(json.dumps(summary, indent=2) + "\n")
for k, v in summary.items():
    print(f"{k:55s} recall {v['recall']['mean']:.3f}+/-{v['recall']['std']:.3f}  FPR {v['fpr']['mean']:.3f}+/-{v['fpr']['std']:.3f}  (runs={v['runs']})")
