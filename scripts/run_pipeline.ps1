# Runs the whole MAPIS pipeline on the GPU laptop and saves every log under results\logs.
# Usage (repo root, venv active):
#   .\scripts\run_pipeline.ps1                 # one full run (seed 42)
#   .\scripts\run_pipeline.ps1 -Seeds 3        # + 2 extra training seeds for MAPIS and stateless -> results\seeds, aggregated mean +/- std
#   .\scripts\run_pipeline.ps1 -SkipLlamaGuard # skip the Llama Guard step (its result does not change between runs)
param([int]$Seeds = 1, [switch]$SkipLlamaGuard, [string]$Model = "")
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force results\logs | Out-Null
$sets = "multihop,realharm,v1,decomposed,bipia"
$modelArg = if ($Model) { "--model-name $Model" } else { "" }

function Step($name, $cmd, [bool]$Optional = $false) {
    Write-Host "`n=== $name ===" -ForegroundColor Cyan
    $log = "results\logs\$name.txt"
    & cmd /c "$cmd 2>&1" | Tee-Object -FilePath $log
    if ($LASTEXITCODE -ne 0) {
        if ($Optional) { Write-Host "Step '$name' failed (see $log) - continuing" -ForegroundColor Yellow } else { throw "Step '$name' failed (see $log)" }
    }
}

Step "00_code_version"     "git log --oneline -1 && python -c ""import backend.core.features as F, pathlib; assert hasattr(F, 'escalation_risk') and pathlib.Path('data/mapis_bench/mapis_bench_realharm_v1.jsonl').exists(), 'OLD CODE: run git stash; git pull first'; print('code check ok')"""
Step "0_multihop_set"      "python scripts/generate_multihop.py"
Step "0b_realharm_set"     "python scripts/dataset_build/convert_realharm.py"
Step "1_prepare_data"      "python scripts/prepare_phase4_training_data.py"
Step "2_validate_data"     "python scripts/validate_phase4_training_data.py"
Step "3_train_stateful"    "python -m backend.ml.train --run $modelArg"
Step "4_train_stateless"   "python -m backend.ml.train --run --no-context --output-dir artifacts/mapis_stateless $modelArg"
Step "5_decomposed_set"    "python scripts/generate_decomposed.py"
Step "6_evaluate"          "python -m backend.ml.evaluate --model artifacts/mapis_detector --stateless artifacts/mapis_stateless --out results/evaluate.json"
Step "7_benchmark"         "python scripts/benchmark.py --systems mapis,mapis-model,mapis-no-provenance,mapis-stateless,regex --sets $sets"
Step "8_false_positives"   "python scripts/diagnose.py --sets v1 --kind benign"
Step "9_missed_attacks"    "python scripts/diagnose.py --sets multihop,realharm --kind attack --limit 15"
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
Write-Host "  results\benchmark.json, results\benchmark_llamaguard.json, results\evaluate.json, results\logs\ (whole folder), results\seeds\ (if it exists)"
Write-Host "  artifacts\mapis_detector\calibration.json, history.json, training_config.json"
Write-Host "  artifacts\mapis_stateless\calibration.json, history.json"
Write-Host "  (never the .safetensors model files)"
