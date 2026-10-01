# MAPIS status (verified in this repository)

## Implemented and tested (pytest, no GPU needed)
- Four-tier response PASS / FLAG / QUARANTINE / BLOCK on the 0=malicious scale, channel suspension, quarantine review API.
- Session store: Redis with in-memory fallback; bounded window; goal vector text never overwritten by agent output.
- Four stateful signals + noisy-OR fusion + session sensitivity; forensic propagation trace (origin → relay → action).
- 5-agent LangGraph testbed over a simulated environment (web / files / memory / email); tap on every hop incl. memory writes/reads and tool calls.
- FastAPI tap, SQLite forensic log, WebSocket push, React dashboard (timeline, alerts, traces, quarantine review).
- Training / calibration (temperature) / evaluation code; train/serve text parity is unit-tested.

## NOT yet measured (needs the laptop)
- Any DeBERTa result. Slide-9 numbers (89.97 % acc, 87.5 % recall, 4.35 % FPR) cannot be reproduced from this repo until the model is retrained.
- Latency of the full shield with the transformer; thresholds tuned on validation.
- Llama Guard / NeMo baselines (adapters written, never run).

## Known limits to state openly
- MAPIS-Bench v1 labels the injection-bearing *tool event*; most attacks there are single-injection, so v1 alone cannot show a
  stateful advantage. `scripts/generate_decomposed.py` builds template-seeded decomposed attacks (split by template family) for that.
  It is synthetic and was written around the provenance mechanism, so results on it demonstrate the mechanism, not real-world recall.
- Possible label shortcut (role / `<INFORMATION>` marker) in the Phase-4 labels: `backend/ml/evaluate.py` includes diagnostics.
- Provenance can false-positive when a legitimate destination comes from a tool result (e.g. "pay the bill in the file").
  Those land in QUARANTINE for a human, and the false-positive cost is measured on the benign sessions in the benchmark.
- Fusion weights are defaults; tune on validation before the final review.
- AutoGen is not implemented (LangGraph only).
