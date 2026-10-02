# Runs the whole MAPIS pipeline on the GPU laptop and saves every log under results\logs.
# Usage (from the repo root, venv active):   .\scripts\run_pipeline.ps1
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force results\logs | Out-Null

function Step($name, $cmd, [bool]$Optional = $false) {
    Write-Host "`n=== $name ===" -ForegroundColor Cyan
    $log = "results\logs\$name.txt"
    & cmd /c "$cmd 2>&1" | Tee-Object -FilePath $log
    if ($LASTEXITCODE -ne 0) {
        if ($Optional) { Write-Host "Step '$name' failed (see $log) - continuing" -ForegroundColor Yellow } else { throw "Step '$name' failed (see $log)" }
    }
}

Step "00_code_version"     "git log --oneline -1 && python -c ""from backend.core.context import render_signals; import backend.core.features as F; assert hasattr(F, 'escalation_risk'), 'OLD CODE: run git pull first'; print('code check ok')"""
Step "0_multihop_set"      "python scripts/generate_multihop.py"
Step "1_prepare_data"      "python scripts/prepare_phase4_training_data.py"
Step "2_validate_data"     "python scripts/validate_phase4_training_data.py"
Step "3_train_stateful"    "python -m backend.ml.train --run"
Step "4_train_stateless"   "python -m backend.ml.train --run --no-context --output-dir artifacts/mapis_stateless"
Step "5_decomposed_set"    "python scripts/generate_decomposed.py"
Step "6_evaluate"          "python -m backend.ml.evaluate --model artifacts/mapis_detector --stateless artifacts/mapis_stateless"
Step "7_benchmark"         "python scripts/benchmark.py --systems mapis,mapis-model,mapis-no-provenance,mapis-stateless,regex --sets multihop,v1,decomposed,bipia"
Step "8_false_positives"   "python scripts/diagnose.py --sets v1 --kind benign"
Step "9_missed_attacks"    "python scripts/diagnose.py --sets bipia --kind attack --limit 8"

Step "10_llamaguard"       "python scripts/benchmark.py --systems llamaguard --sets multihop,v1,decomposed,bipia --out results/benchmark_llamaguard.json" $true

Write-Host "`nDONE. Upload the 'results' folder (including results\logs) and these small files to the Drive folder 'mapis_results':" -ForegroundColor Green
Write-Host "  artifacts\mapis_detector\calibration.json, history.json, training_config.json"
Write-Host "  artifacts\mapis_stateless\calibration.json, history.json"
