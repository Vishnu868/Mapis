# Final remaining runs for the paper (LLM-based baselines on a larger test subset, optional larger judge model).
# Usage (repo root, venv active, Ollama running with qwen2.5:7b pulled):
#   .\scripts\run_remaining.ps1            # NeMo Guardrails + history-aware LLM judge, qwen2.5:7b, ~460-session class-balanced subset
#   .\scripts\run_remaining.ps1 -Big       # also the LLM judge with qwen2.5:14b on the 20-per-set subset (needs a 16 GB laptop)
#   .\scripts\run_remaining.ps1 -BigOnly   # only the 14B judge
# Every LLM reply is cached in results\llm_cache, so an interrupted run resumes where it stopped (just run the same command again).
param([switch]$Big, [switch]$BigOnly, [int]$PerSet = 60)
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force results\logs | Out-Null
$sets = "multihop,adaptive,realharm,v1,decomposed,bipia"

function Step($name, $cmd) {
    Write-Host "`n=== $name ===" -ForegroundColor Cyan
    $log = "results\logs\$name.txt"
    & cmd /c "$cmd 2>&1" | Tee-Object -FilePath $log
    if ($LASTEXITCODE -ne 0) { throw "Step '$name' failed (see $log)" }
}

# 0. checks: code version, Ollama server, model
if (-not (Select-String -Path scripts\benchmark.py -Pattern "max-per-set" -Quiet)) { throw "old code: run git pull first" }
try { $tags = Invoke-RestMethod http://localhost:11434/api/tags -TimeoutSec 5 } catch { throw "Ollama is not running: start the Ollama app (or 'ollama serve') and try again" }
$env:LLM_BASE_URL = "http://localhost:11434/v1"
$env:LLM_API_KEY = "ollama"
$env:LLM_RPM = "600"

if (-not $BigOnly) {
    if (-not ($tags.models.name -contains "qwen2.5:7b")) { Step "final_0_pull_7b" "ollama pull qwen2.5:7b" }
    $env:LLM_MODEL = "qwen2.5:7b"
    # MAPIS and the stateless model are re-scored on exactly the same subset, so the table is like-for-like
    Step "final_1_llm_baselines_7b" "python scripts/benchmark.py --systems mapis,mapis-stateless,llmjudge,nemo --sets $sets --max-per-set $PerSet --out results/benchmark_llm$PerSet.json"
}

if ($Big -or $BigOnly) {
    $ramGB = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)
    if ($ramGB -lt 15) {  # Windows reports a 16 GB laptop as ~15 GB (memory reserved by hardware/GPU)
        Write-Host "Skipping the 14B judge: this laptop has $ramGB GB RAM (16 GB needed)." -ForegroundColor Yellow
    } else {
        if (-not ($tags.models.name -contains "qwen2.5:14b")) { Step "final_2_pull_14b" "ollama pull qwen2.5:14b" }
        $env:LLM_MODEL = "qwen2.5:14b"
        Step "final_3_llm_judge_14b" "python scripts/benchmark.py --systems mapis,mapis-stateless,llmjudge --sets $sets --max-per-set 20 --out results/benchmark_llm_14b.json"
    }
}

Write-Host "`nDONE. Upload to Drive mapis_results:" -ForegroundColor Green
Write-Host "  results\benchmark_llm$PerSet.json"
if ($Big -or $BigOnly) { Write-Host "  results\benchmark_llm_14b.json (if it was created)" }
Write-Host "  results\logs\ (whole folder)"
Write-Host "  artifacts\seed2\mapis_detector\training_config.json ... artifacts\seed5\mapis_detector\training_config.json (the four files; they record the random seed of each run)"
