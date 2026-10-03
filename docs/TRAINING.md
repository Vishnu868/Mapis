# Training, evaluating and benchmarking (run on the RTX 3050 laptop)

```bash
git pull && pip install -r requirements.txt
# Needs data/mapis_bench/mapis_bench_v1.jsonl and mapis_bench_bipia_v1.jsonl (both committed). Build the v3 events first.
# v3 = chunked events, hard negatives, BIPIA, held-out templates. Do NOT use any older events file.
python scripts/prepare_phase4_training_data.py && python scripts/validate_phase4_training_data.py   # REQUIRED: builds data/training/mapis_phase4_events_v4.jsonl (deterministic, ~1 min)

# 1. stateful detector  (~5k chunk rows x 3 epochs, 512 tokens; expect roughly 1-2 h on a 3050, batch 4 x 4 accumulation, fp16)
python -m backend.ml.train --run
# 2. stateless ablation, same model, current event only (for the comparison)
python -m backend.ml.train --run --no-context --output-dir artifacts/mapis_stateless

# 3. test + test_ood metrics with cheap baselines on the same rows (run ONCE, after you stop changing things)
python -m backend.ml.evaluate --model artifacts/mapis_detector --stateless artifacts/mapis_stateless

# 4. session-level benchmark: MAPIS vs ablations vs baselines on identical events
python scripts/generate_decomposed.py
python scripts/benchmark.py --systems mapis,mapis-no-provenance,mapis-stateless,regex --sets v1,decomposed,bipia
# Llama Guard / NeMo (need gated weights / an OpenAI key):
python scripts/benchmark.py --systems llamaguard,promptguard,nemo --sets v1,decomposed,bipia
```
Outputs land in `artifacts/` (weights, calibration.json, history.json) and `results/` (metrics JSON).
Send `results/*.json` and `artifacts/mapis_detector/{calibration,history,training_config}.json` back; the weights themselves need not be shared unless you want them committed.

Reading the results
- Metrics are EVENT-level: a long event is split into overlapping chunks and its trust is the minimum over chunks.
- `test` = unseen sessions, same attack templates. `test_ood` = attack templates never seen in training (AgentDojo `tool_knowledge`, a quarter of the InjecAgent instructions).
  `test_bipia` = a different dataset altogether (BIPIA's own test contexts and attack categories, never trained on): the generalisation number to quote.
- `baselines_same_events` (role-only, length-only, TF-IDF + logistic regression) show what a cheap model scores on the identical events. On AgentDojo / InjecAgent a lexical model already scores
  ~99-100 %, because injected instructions are blatantly imperative; only `test_bipia` separates models. The stateful claim rests on the decomposed benchmark
  (`scripts/benchmark.py --sets decomposed`) where no single message contains an instruction.
