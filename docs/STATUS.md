# MAPIS status (verified in this repository)

## Implemented and tested (pytest, no GPU needed)
- Four-tier response PASS / FLAG / QUARANTINE / BLOCK on the 0=malicious scale, channel suspension, quarantine review API.
- Session store: Redis with in-memory fallback; bounded window; goal vector text never overwritten by agent output.
- Four stateful signals + noisy-OR fusion + session sensitivity; forensic propagation trace (origin → relay → action).
- 5-agent LangGraph testbed over a simulated environment (web / files / memory / email); tap on every hop incl. memory writes/reads and tool calls.
- FastAPI tap, SQLite forensic log, WebSocket push, React dashboard (timeline, alerts, traces, quarantine review).
- Training / calibration (temperature) / evaluation code; train/serve text parity is unit-tested.

## NOT yet measured (needs the laptop)
- Any DeBERTa result. No completed training exists (only an abandoned epoch-1 checkpoint on an old CPU laptop). The First Review slide figures
  (89.97 % acc, 87.5 % recall, 4.35 % FPR, TP 231 / FN 33 / FP 5 / TN 110) are provisional placeholders and must be removed from the deck.
- The only real quantitative result is the old heuristic baseline on MAPIS-Bench v1 test (282 sessions): recall 10.55 %, precision 96.43 %, FPR 3.85 %.
- Latency of the full shield with the transformer; thresholds tuned on validation.
- Llama Guard / NeMo baselines (adapters written, never run).

## Known limits to state openly
- MAPIS-Bench v1 labels the injection-bearing *tool event*; most attacks there are single-injection, so v1 alone cannot show a
  stateful advantage. `scripts/generate_decomposed.py` builds template-seeded decomposed attacks (split by template family) for that.
  It is synthetic and was written around the provenance mechanism, so results on it demonstrate the mechanism, not real-world recall.
- Possible label shortcut (role / `<INFORMATION>` marker) in the Phase-4 labels. Mitigated by training-time marker dropout (`marker_dropout=0.5`)
  and checked by `backend/ml/evaluate.py` (role-only baseline, marker-stripped re-score, per-source metrics).
- Provenance can false-positive when a legitimate destination comes from a tool result (e.g. "pay the bill in the file").
  Sources the user explicitly named in the task (e.g. the file in 'pay the bill in bill.txt') are trusted origins; anything else lands in QUARANTINE
  for a human. The remaining false-positive cost is measured on the benign sessions in the benchmark.
- Fusion weights are defaults; tune on validation before the final review.
- AutoGen is not implemented (LangGraph only).
