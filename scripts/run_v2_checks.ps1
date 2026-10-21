# MAPIS-v2 (action-argument tampering checks) vs MAPIS on every test set, with the trained models. No retraining needed:
# the classifier input is unchanged; v2 only adds rule checks in the fusion step.  ~1-1.5 h on the RTX 3050.
#   .\scripts\run_v2_checks.ps1
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force results\logs, results\v2 | Out-Null
$sets = "multihop,adaptive,realharm,v1,decomposed,bipia,stateattack,independent"
function Step($name, $cmd) {
    Write-Host "`n=== $name ===" -ForegroundColor Cyan
    & cmd /c "$cmd 2>&1" | Tee-Object -FilePath "results\logs\v2_$name.txt"
}
Step "1_rebuild_sets" "python scripts/generate_stateattack.py && python scripts/dataset_build/build_independent.py"
Step "2_seed42" "python scripts/benchmark.py --systems mapis,mapis-v2 --sets $sets --out results/v2/benchmark_seed42.json"
foreach ($k in 2..9) {
    if (Test-Path "artifacts\seed$k\mapis_detector") {
        Step "3_seed$k" "python scripts/benchmark.py --systems mapis,mapis-v2 --sets $sets --model artifacts/seed$k/mapis_detector --out results/v2/benchmark_seed$k.json"
    }
}
Write-Host "`nDONE. Upload to Drive mapis_results: results\v2\ (folder) and results\logs\ (folder)" -ForegroundColor Green
