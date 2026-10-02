"""Replay MAPIS-Bench sessions through each system and report session-level metrics.

    python scripts/benchmark.py --systems mapis,mapis-stateless,regex
    python scripts/benchmark.py --systems mapis,llamaguard,nemo --sets v1,decomposed,bipia --split test

A session counts as *detected* when any event is held back (QUARANTINE/BLOCK for MAPIS, 'unsafe'
for a stateless baseline).  False-positive rate = benign sessions with any held-back event.
Every system sees exactly the same events in the same order.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import uuid
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.config import Settings  # noqa: E402
from backend.core.shield import MapisShield, Tier  # noqa: E402
from backend.core.store import MemoryStore  # noqa: E402
from backend.ml.metrics import confusion, summarize  # noqa: E402

DATASETS = {"v1": ROOT / "data/mapis_bench/mapis_bench_v1.jsonl", "decomposed": ROOT / "data/mapis_bench/mapis_bench_decomposed_v1.jsonl",
            "bipia": ROOT / "data/mapis_bench/mapis_bench_bipia_v1.jsonl"}
NOT_RUNTIME = {"attacker_instruction", "tool_response_template"}  # derived annotations, not events an agent would emit


def load(sets: list[str], split: str) -> list[dict]:
    rows = []
    for name in sets:
        path = DATASETS[name]
        if not path.exists():
            print(f"[skip] {path} not found")
            continue
        wanted = "external" if name == "bipia" and split == "test" else split  # BIPIA's own test contexts + categories
        rows += [r for r in (json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()) if r["split"] == wanted]
    return rows


def events(sample: dict):
    for m in sample["messages"]:
        if m["role"] not in NOT_RUNTIME:
            yield {k: m.get(k) for k in ("role", "source", "target", "content", "tool_name", "tool_call", "tool_calls", "tool_response")}


class ShieldSystem:
    def __init__(self, name: str, shield: MapisShield, hold_from: Tier = Tier.QUARANTINE):
        self.name, self.shield, self.hold_from = name, shield, hold_from

    def run(self, sample: dict) -> tuple[bool, list[float]]:
        sid, held, lat = uuid.uuid4().hex, False, []
        for e in events(sample):
            v = self.shield.inspect({"session_id": sid, **e})
            lat.append(v.latency_ms)
            held |= v.tier.severity >= self.hold_from.severity
        self.shield.reset(sid)
        return held, lat


class StatelessSystem:
    """Wraps a content detector that sees one message at a time."""

    def __init__(self, detector, threshold: float = 0.5):
        self.name, self.detector, self.threshold = detector.name, detector, threshold

    def run(self, sample: dict) -> tuple[bool, list[float]]:
        import time
        from backend.core.context import build_texts, normalize_hop
        held, lat = False, []
        for i, e in enumerate(events(sample), 1):
            if e["role"] in ("user", "system"):
                continue
            hop = normalize_hop({**e, "hop": i})
            t0 = time.perf_counter()
            held |= self.detector.score_chunks(build_texts([], hop), hop)[0] < self.threshold
            lat.append(1000 * (time.perf_counter() - t0))
        return held, lat


def build(name: str, model: str, stateless_model: str):
    cfg = Settings(redis_url="", model_path=model)
    if name == "mapis":
        return ShieldSystem("mapis", MapisShield(cfg, MemoryStore()))
    if name == "mapis-no-provenance":  # ablation: model + instruction cue, no cross-hop provenance
        return ShieldSystem(name, MapisShield(cfg, MemoryStore(), features_enabled=("instruction",)))
    if name == "mapis-stateless":  # same transformer family trained on the current event only
        from backend.core.detector import load_detector
        return StatelessSystem(load_detector(stateless_model))
    if name == "regex":
        from backend.core.detector import RegexDetector
        return StatelessSystem(RegexDetector())
    if name == "llamaguard":
        from backend.baselines import LlamaGuardBaseline
        return StatelessSystem(LlamaGuardBaseline())
    if name == "promptguard":
        from backend.baselines import PromptGuardBaseline
        return StatelessSystem(PromptGuardBaseline())
    if name == "nemo":
        from backend.baselines import NemoBaseline
        return StatelessSystem(NemoBaseline())
    raise SystemExit(f"unknown system {name}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--systems", default="mapis,mapis-stateless,regex")
    ap.add_argument("--sets", default="v1,decomposed")
    ap.add_argument("--split", default="test")
    ap.add_argument("--model", default="artifacts/mapis_detector")
    ap.add_argument("--stateless-model", default="artifacts/mapis_stateless")
    ap.add_argument("--out", default="results/benchmark.json")
    args = ap.parse_args()

    samples = load(args.sets.split(","), args.split)
    print(f"{len(samples)} sessions ({args.sets}, split={args.split})")
    report = {}
    for name in args.systems.split(","):
        system = build(name, args.model, args.stateless_model)
        flags, labels, lats, by_set, by_class = [], [], [], defaultdict(lambda: ([], [])), defaultdict(list)
        for s in samples:
            held, lat = system.run(s)
            y = 0 if s["is_attack"] else 1
            flags.append(held); labels.append(y); lats += lat
            set_name = {"MAPIS-Decomposed": "MAPIS-Decomposed", "BIPIA": "BIPIA (unseen dataset)"}.get(s["source_dataset"], "MAPIS-Bench v1")
            by_set[set_name][0].append(y); by_set[set_name][1].append(held)
            if s.get("benign_kind"):  # benign sessions reported separately by kind
                by_set[f"benign: {s['benign_kind']}"][0].append(y); by_set[f"benign: {s['benign_kind']}"][1].append(held)
            if s["is_attack"]:
                by_class[s["mapis_attack_class"]].append(held)
        report[system.name] = {
            "overall": summarize(confusion(labels, flags)),
            "by_set": {k: summarize(confusion(*v)) for k, v in by_set.items()},
            "recall_by_attack_class": {str(k): {"n": len(v), "recall": round(sum(v) / len(v), 4)} for k, v in by_class.items()},
            "latency_ms_per_event": {"mean": round(statistics.fmean(lats), 2), "p95": round(sorted(lats)[int(0.95 * len(lats))], 2)} if lats else None,
        }
        o = report[system.name]["overall"]
        ci = lambda m, key: f"[{m[key + '_ci95'][0]:.2f}-{m[key + '_ci95'][1]:.2f}]"  # noqa: E731
        print(f"{system.name:22s} recall {o['recall']:.3f} {ci(o, 'recall')}  FPR {o['fpr']:.3f} {ci(o, 'fpr')}  F1 {o['f1']:.3f}  acc {o['accuracy']:.3f}")
        for k, v in report[system.name]["by_set"].items():
            print(f"   {k:44s} recall {v['recall']:.3f}  FPR {v['fpr']:.3f} {ci(v, 'fpr')}  (n={v['n']})")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
