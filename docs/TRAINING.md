# Training, evaluating and benchmarking (run on the RTX 3050 laptop)

```bash
git pull && pip install -r requirements.txt
# Needs: data/mapis_bench/mapis_bench_v1.jsonl  and  data/training/mapis_phase4_events_v1.jsonl
python scripts/prepare_phase4_training_data.py && python scripts/validate_phase4_training_data.py   # optional: regenerate + validate

# 1. stateful detector  (~ 30-60 min on a 3050; batch 4 x 4 accumulation, mixed precision)
python -m backend.ml.train --run
# 2. stateless ablation, same model, current event only (for the comparison)
python -m backend.ml.train --run --no-context --output-dir artifacts/mapis_stateless

# 3. headline test metrics + shortcut diagnostics (run ONCE, after you stop changing things)
python -m backend.ml.evaluate --model artifacts/mapis_detector --stateless artifacts/mapis_stateless

# 4. session-level benchmark: MAPIS vs ablations vs baselines on identical events
python scripts/generate_decomposed.py
python scripts/benchmark.py --systems mapis,mapis-no-provenance,mapis-stateless,regex --sets v1,decomposed
# Llama Guard / NeMo (need gated weights / an OpenAI key):
python scripts/benchmark.py --systems llamaguard,nemo --sets v1,decomposed
```
Outputs land in `artifacts/` (weights, calibration.json, history.json) and `results/` (metrics JSON).
Send `results/*.json` and `artifacts/mapis_detector/{calibration,history,training_config}.json` back; the weights themselves need not be shared unless you want them committed.

Reading the diagnostics: if `diagnostic_role_only_baseline` scores close to the model, or
`diagnostic_markers_stripped` collapses, the classifier is using dataset artifacts, not injection semantics.
