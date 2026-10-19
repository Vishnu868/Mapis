# Final evidence checks on the trained models (no training; ~1-2 h on the RTX 3050). Logs in results\logs\final_*.txt.
#   1. validation-calibrated hold cut-off per seed           -> results\calibration\seed*.json
#   2. MAPIS-StateAttack (test-only, aims at the session record) for every seed, MAPIS vs model-only vs stateless vs regex
#                                                             -> results\stateattack\seed*.json
#   3. rule ablation (full / model only / no provenance) on adaptive, multi-hop, StateAttack, independent (if present)
#                                                             -> results\ablation_seed42.json
# Usage (repo root, venv active):  .\scripts\run_final_checks.ps1
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force results\logs, results\calibration, results\stateattack | Out-Null

function Step($name, $cmd) {
    Write-Host "`n=== $name ===" -ForegroundColor Cyan
    & cmd /c "$cmd 2>&1" | Tee-Object -FilePath "results\logs\final_$name.txt"
    if ($LASTEXITCODE -ne 0) { Write-Host "Step '$name' failed - continuing" -ForegroundColor Yellow }
}

Step "00_build_sets" "python scripts/generate_stateattack.py"
if (Get-ChildItem data\independent\*.json -Exclude EXAMPLE* -ErrorAction SilentlyContinue) {
    Step "00_build_independent" "python scripts/dataset_build/build_independent.py"
    $abl = "adaptive,multihop,stateattack,independent"
} else { $abl = "adaptive,multihop,stateattack" }

$seeds = @(@{n="42"; d="artifacts"})
foreach ($k in 2..9) { if (Test-Path "artifacts\seed$k\mapis_detector") { $seeds += @{n="$k"; d="artifacts\seed$k"} } }
foreach ($s in $seeds) {
    $m = "$($s.d)\mapis_detector"; $st = "$($s.d)\mapis_stateless"
    Step "1_calibrate_seed$($s.n)" "python scripts/calibrate_mapis.py --model $m --out results/calibration/seed$($s.n).json"
    Step "2_stateattack_seed$($s.n)" "python scripts/benchmark.py --systems mapis,mapis-model,mapis-stateless,regex --sets stateattack --model $m --stateless-model $st --out results/stateattack/seed$($s.n).json"
}
Step "3_ablation_seed42" "python scripts/benchmark.py --systems mapis,mapis-model,mapis-no-provenance --sets $abl --out results/ablation_seed42.json"
if (Test-Path data\mapis_bench\mapis_bench_independent_v1.jsonl) {
    Step "4_independent" "python scripts/benchmark.py --systems mapis,mapis-stateless,protectai,llamaguard --sets independent --out results/benchmark_independent.json"
}
Write-Host "`nDONE. Upload to Drive mapis_results: results\calibration\ (folder), results\stateattack\ (folder), results\ablation_seed42.json, results\benchmark_independent.json (if made), results\logs\ (folder)" -ForegroundColor Green
