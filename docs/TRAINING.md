# Training, evaluating and benchmarking (run on the RTX 3050 laptop)

```bash
git pull && pip install -r requirements.txt
# Needs only data/mapis_bench/mapis_bench_v1.jsonl (committed). Build the v2 events from it first:
# v2 = hard negatives + held-out templates. Do NOT train on the old v1 events file.
python scripts/prepare_phase4_training_data.py && python scripts/validate_phase4_training_data.py   # REQUIRED: builds data/training/mapis_phase4_events_v2.jsonl (deterministic, ~1 min)

# 1. stateful detector  (~ 30-60 min on a 3050; batch 4 x 4 accumulation, mixed precision)
python -m backend.ml.train --run
# 2. stateless ablation, same model, current event only (for the comparison)
python -m backend.ml.train --run --no-context --output-dir artifacts/mapis_stateless

# 3. test + test_ood metrics with cheap baselines on the same rows (run ONCE, after you stop changing things)
python -m backend.ml.evaluate --model artifacts/mapis_detector --stateless artifacts/mapis_stateless

# 4. session-level benchmark: MAPIS vs ablations vs baselines on identical events
python scripts/generate_decomposed.py
python scripts/benchmark.py --systems mapis,mapis-no-provenance,mapis-stateless,regex --sets v1,decomposed
# Llama Guard / NeMo (need gated weights / an OpenAI key):
python scripts/benchmark.py --systems llamaguard,nemo --sets v1,decomposed
```
Outputs land in `artifacts/` (weights, calibration.json, history.json) and `results/` (metrics JSON).
Send `results/*.json` and `artifacts/mapis_detector/{calibration,history,training_config}.json` back; the weights themselves need not be shared unless you want them committed.

Reading the results
- `test` = unseen sessions, same attack templates. `test_ood` = attack templates never seen in training (AgentDojo `tool_knowledge`, a quarter of the InjecAgent instructions). Quote `test_ood` as the generalisation number.
- `baselines_same_rows` (role-only, length-only, TF-IDF + logistic regression) show what a cheap model scores on the identical rows. On these public benchmarks a lexical model
  already scores ~98-100 %, because injected instructions are blatantly imperative. A DeBERTa number is therefore NOT evidence of an advantage by itself; the stateful claim rests on
  the decomposed benchmark (`scripts/benchmark.py --sets decomposed`) where no single message contains an instruction.
