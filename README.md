# MAPIS — Multi-Agent Prompt Injection Shield

Stateful, trust-scoring middleware that sits on the communication layer of a multi-agent LLM
pipeline and stops **indirect** prompt injection — including attacks decomposed into
individually-harmless fragments across agent hops.

Trust scale everywhere: **0 = malicious, 1 = safe**.

| Tier | Trust | Action |
|---|---|---|
| PASS | ≥ 0.75 | deliver |
| FLAG | 0.50 – 0.75 | deliver, tag, raise session sensitivity |
| QUARANTINE | 0.25 – 0.50 | hold, alert an operator (release / reject in the dashboard) |
| BLOCK | < 0.25 | drop, suspend the channel, write the propagation trace |

## How a message is judged (`backend/core/shield.py`)
1. The tap (`POST /api/v1/inspect`, or `shield.inspect()` in-process) receives an event: message, tool output, memory read/write or tool call.
2. The session window (Redis, in-memory fallback) supplies the previous hops and the user's goal.
3. **Classifier** — fine-tuned DeBERTa-v3-small reads the causal window + current event → P(safe). Same text renderer as training (`backend/core/context.py`).
4. **Four stateful signals** (`backend/core/features.py`): instruction-in-data, goal drift, cross-hop provenance, behavioural anomaly. Combined with the classifier by noisy-OR; each FLAG raises later sensitivity.
5. Tier → action → verdict + forensic trace (`origin → relay → action`) in SQLite; live push to the dashboard.

## Layout
```
backend/core      shield, features, detector, session store, context renderer
backend/ml        train / calibrate / evaluate the DeBERTa detector
backend/agents    deterministic 5-agent testbed + LangGraph with the tap on every hop
backend/api       REST + WebSocket          backend/db.py  forensic log
scripts/          benchmark.py, generate_decomposed.py, phase-4 data prep/validation, dataset_build/ (provenance of MAPIS-Bench v1)
frontend/         React dashboard           tests/  pytest suite
```

## Run
```bash
pip install -r requirements.txt
docker run -d -p 6379:6379 redis:7-alpine          # optional; falls back to in-memory
uvicorn backend.main:app --port 8000               # regex fallback detector until a model is trained
cd frontend && npm install && npm start            # dashboard on :3000
pytest                                             # 14+ tests
```
Training the detector, evaluation and benchmarks: see **docs/TRAINING.md**.

## Honest status
See `docs/STATUS.md` for what is verified, what is measured, and what is still to do.
