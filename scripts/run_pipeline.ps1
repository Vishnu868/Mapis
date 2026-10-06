# Runs the whole MAPIS pipeline on the GPU laptop and saves every log under results\logs.
# Usage (repo root, venv active):
#   .\scripts\run_pipeline.ps1                 # one full run (seed 42)
#   .\scripts\run_pipeline.ps1 -Seeds 3        # + 2 extra training seeds for MAPIS and stateless -> results\seeds, aggregated mean +/- std
#   .\scripts\run_pipeline.ps1 -SkipLlamaGuard # skip the Llama Guard step (its result does not change between runs)
#   .\scripts\run_pipeline.ps1 -Live          # live LLM agents on AgentDojo with/without MAPIS (needs Ollama or LLM_* variables, see scripts/live_agentdojo.py)
#   .\scripts\run_pipeline.ps1 -LLMBaselines  # history-aware LLM judge + NeMo Guardrails (needs LLM_BASE_URL / LLM_MODEL / LLM_API_KEY)
#   .\scripts\run_pipeline.ps1 -Base          # DeBERTa-v3-base instead of small (slower, more accurate); outputs go to artifacts\base\ and results\base\
param([int]$Seeds = 1, [switch]$SkipLlamaGuard, [string]$Model = "", [switch]$Base, [switch]$Live, [switch]$LLMBaselines, [int]$LLMSample = 60)
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force results\logs | Out-Null
$sets = "multihop,adaptive,realharm,v1,decomposed,bipia"
$modelArg = if ($Base) { "--base" } elseif ($Model) { "--model-name $Model" } else { "" }

function Step($name, $cmd, [bool]$Optional = $false) {
    Write-Host "`n=== $name ===" -ForegroundColor Cyan
    $log = "results\logs\$name.txt"
    & cmd /c "$cmd 2>&1" | Tee-Object -FilePath $log
    if ($LASTEXITCODE -ne 0) {
        if ($Optional) { Write-Host "Step '$name' failed (see $log) - continuing" -ForegroundColor Yellow } else { throw "Step '$name' failed (see $log)" }
    }
}

if ($Live) {
    Step "live_1_agentdojo" "python scripts/live_agentdojo.py --defenses none,mapis,stateless,protectai --suites banking,slack,workspace,travel --user-tasks 4 --injection-tasks 2"
    Write-Host "`nDONE (live). Upload results\live_agentdojo.json and results\logs\ (whole folder)" -ForegroundColor Green
    exit 0
}
if ($LLMBaselines) {
    # class-balanced subset of every test set (free API tiers); MAPIS and the stateless model are re-scored on exactly the same subset
    Step "llm_1_judge_and_nemo" "python scripts/benchmark.py --systems mapis,mapis-stateless,llmjudge,nemo --sets $sets --max-per-set $LLMSample --out results/benchmark_llm.json"
    Write-Host "`nDONE (LLM baselines). Upload results\benchmark_llm.json and results\logs\ (whole folder)" -ForegroundColor Green
    exit 0
}
if ($Base) {
    New-Item -ItemType Directory -Force results\base | Out-Null
    Step "base_1_prepare_data"     "python scripts/prepare_phase4_training_data.py"
    Step "base_2_train_stateful"   "python -m backend.ml.train --run --base --output-dir artifacts/base/mapis_detector"
    Step "base_3_train_stateless"  "python -m backend.ml.train --run --base --no-context --output-dir artifacts/base/mapis_stateless"
    Step "base_4_evaluate"         "python -m backend.ml.evaluate --model artifacts/base/mapis_detector --stateless artifacts/base/mapis_stateless --out results/base/evaluate.json"
    Step "base_5_benchmark"        "python scripts/benchmark.py --systems mapis,mapis-stateless --sets $sets --model artifacts/base/mapis_detector --stateless-model artifacts/base/mapis_stateless --out results/base/benchmark.json"
    Write-Host "`nDONE (base). Upload results\base\ (whole folder), results\logs\ (whole folder), artifacts\base\mapis_detector\{calibration.json, history.json, training_config.json}, artifacts\base\mapis_stateless\{calibration.json, history.json}" -ForegroundColor Green
    exit 0
}

Step "00_code_version"     "git log --oneline -1 && python -c ""import backend.core.features as F, pathlib; assert hasattr(F, 'canonical') and pathlib.Path('data/mapis_bench/mapis_bench_realharm_v1.jsonl').exists(), 'OLD CODE: run git stash; git pull first'; print('code check ok')"""
if (Test-Path artifacts\mapis_detector\config.json) {
    # BEFORE numbers on the evasive-attacker set: the previous model, with the old indicator matching and with the new canonical matching
    Step "00a_adaptive_before"        "set MAPIS_LEGACY_INDICATORS=1&& python scripts/benchmark.py --systems mapis,mapis-model,mapis-stateless --sets adaptive --out results/adaptive_before.json" $true
    Step "00b_adaptive_old_model_new_rules" "python scripts/benchmark.py --systems mapis,mapis-model --sets adaptive --out results/adaptive_old_model_new_rules.json" $true
}
Step "0_multihop_set"      "python scripts/generate_multihop.py"
Step "0b_realharm_set"     "python scripts/dataset_build/convert_realharm.py"
Step "0c_adaptive_set"     "python scripts/generate_adaptive.py"
Step "1_prepare_data"      "python scripts/prepare_phase4_training_data.py"
Step "2_validate_data"     "python scripts/validate_phase4_training_data.py"
Step "3_train_stateful"    "python -m backend.ml.train --run $modelArg"
Step "4_train_stateless"   "python -m backend.ml.train --run --no-context --output-dir artifacts/mapis_stateless $modelArg"
Step "5_decomposed_set"    "python scripts/generate_decomposed.py"
Step "6_evaluate"          "python -m backend.ml.evaluate --model artifacts/mapis_detector --stateless artifacts/mapis_stateless --out results/evaluate.json"
Step "7_benchmark"         "python scripts/benchmark.py --systems mapis,mapis-model,mapis-no-provenance,mapis-stateless,regex --sets $sets"
Step "8_false_positives"   "python scripts/diagnose.py --sets v1 --kind benign"
Step "9_missed_attacks"    "python scripts/diagnose.py --sets multihop,adaptive,realharm --kind attack --limit 15"
Step "9b_adaptive_false_positives" "python scripts/diagnose.py --sets adaptive --kind benign --limit 15"
Step "10b_injection_classifiers" "python scripts/benchmark.py --systems promptguard,protectai --sets $sets --out results/benchmark_promptguard.json" $true
if (-not $SkipLlamaGuard) {
    Step "10_llamaguard"   "python scripts/benchmark.py --systems llamaguard --sets $sets --out results/benchmark_llamaguard.json" $true
}

for ($s = 2; $s -le $Seeds; $s++) {
    $seed = 40 + $s
    Step "11_seed${s}_train_stateful"  "python -m backend.ml.train --run --seed $seed --output-dir artifacts/seed$s/mapis_detector $modelArg"
    Step "11_seed${s}_train_stateless" "python -m backend.ml.train --run --seed $seed --no-context --output-dir artifacts/seed$s/mapis_stateless $modelArg"
    Step "11_seed${s}_benchmark"       "python scripts/benchmark.py --systems mapis,mapis-stateless --sets $sets --model artifacts/seed$s/mapis_detector --stateless-model artifacts/seed$s/mapis_stateless --out results/seeds/benchmark_seed$s.json"
}
if ($Seeds -gt 1) { Step "12_aggregate_seeds" "python scripts/aggregate_seeds.py" }

Write-Host "`nDONE. Upload to the Drive folder 'mapis_results':" -ForegroundColor Green
Write-Host "  results\benchmark.json, results\benchmark_llamaguard.json, results\benchmark_promptguard.json, results\evaluate.json, results\adaptive_before.json, results\adaptive_old_model_new_rules.json, results\logs\ (whole folder), results\seeds\ (if it exists)"
Write-Host "  artifacts\mapis_detector\calibration.json, history.json, training_config.json"
Write-Host "  artifacts\mapis_stateless\calibration.json, history.json"
Write-Host "  (never the .safetensors model files)"
