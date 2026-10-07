# MAPIS - what to run next (as of 6 Oct 2026, commit ceb972f+)

All code is on branch `claude/inspiring-hopper-4gqkjy` (PR #1). Full project record: `CLAUDE.md` (any new Claude chat: "read CLAUDE.md first").
Every laptop session starts with:
```powershell
cd E:\mapis\mapis\Mapis
& E:\mapis\mapis\Scripts\Activate.ps1
git stash
git pull origin claude/inspiring-hopper-4gqkjy
```
Never upload `*.safetensors`. Upload everything else listed to Drive `mapis_results`.

## Step 1 - finish the base-model run (running now)
Upload: `results\base\`, `results\logs\`, `artifacts\base\mapis_detector\{calibration.json, history.json, training_config.json}`,
`artifacts\base\mapis_stateless\{calibration.json, history.json}`.

## Step 2 - main run with adaptive attacks + new baselines (overnight, ~12 h)
Once: accept the licence at huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M (same HF account as Llama Guard).
```powershell
pip install -r requirements-eval.txt
.\scripts\run_pipeline.ps1 -Seeds 3
```
Upload: `results\benchmark.json`, `results\benchmark_llamaguard.json`, `results\benchmark_promptguard.json`, `results\evaluate.json`,
`results\adaptive_before.json`, `results\adaptive_old_model_new_rules.json`, `results\logs\`, `results\seeds\`,
`artifacts\mapis_detector\{calibration.json, history.json, training_config.json}`, `artifacts\mapis_stateless\{calibration.json, history.json}`.

## Step 2b - gated Hugging Face models (only if step 10 / 10c of the main run failed with 401)
Cause: a stale `HF_TOKEN` environment variable overrides the saved login. Fix in a NEW PowerShell window after the main run finished:
```powershell
cd E:\mapis\mapis\Mapis
& E:\mapis\mapis\Scripts\Activate.ps1
Remove-Item Env:HF_TOKEN -ErrorAction SilentlyContinue
[Environment]::SetEnvironmentVariable("HF_TOKEN", $null, "User")   # removes a persistent stale one
hf auth login          # paste a NEW Read token from huggingface.co/settings/tokens (same account that accepted the licences)
hf auth whoami
python scripts/benchmark.py --systems protectai --sets multihop,adaptive,realharm,v1,decomposed,bipia --out results/benchmark_protectai.json
python scripts/benchmark.py --systems promptguard --sets multihop,adaptive,realharm,v1,decomposed,bipia --out results/benchmark_promptguard.json
python scripts/benchmark.py --systems llamaguard --sets multihop,adaptive,realharm,v1,decomposed,bipia --out results/benchmark_llamaguard.json
```
Upload: `results\benchmark_protectai.json`, `results\benchmark_promptguard.json`, `results\benchmark_llamaguard.json`.

## Step 3 - live LLM agents on AgentDojo (free, ~7-10 h)
Install Ollama (ollama.com), then `ollama pull qwen2.5:7b`.
```powershell
$env:LLM_BASE_URL="http://localhost:11434/v1"; $env:LLM_MODEL="qwen2.5:7b"; $env:LLM_API_KEY="ollama"
.\scripts\run_pipeline.ps1 -Live
```
Upload: `results\live_agentdojo.json`, `results\logs\`.

## Step 4 - LLM judge + NeMo Guardrails (no GPU; can run alongside step 3)
Free key from console.groq.com - type it only in the shell, never in chat or files.
```powershell
$env:LLM_BASE_URL="https://api.groq.com/openai/v1"; $env:LLM_MODEL="llama-3.3-70b-versatile"; $env:LLM_API_KEY="<your key>"; $env:LLM_RPM="25"
.\scripts\run_pipeline.ps1 -LLMBaselines
```
If the daily limit stops it, rerun the same command next day (answers are cached). Upload: `results\benchmark_llm.json`, `results\logs\`.

## Step 5 - team independent test set
Each member follows `docs/INDEPENDENT_TESTSET_GUIDE.md`, then:
```powershell
python scripts/dataset_build/build_independent.py
python scripts/benchmark.py --systems mapis,mapis-stateless,llamaguard --sets independent --out results/benchmark_independent.json
```
Upload: `results\benchmark_independent.json`.

## Step 6 - after results are in (with Claude)
Ask Claude to read CLAUDE.md + the Drive files, record final numbers, then: retake dashboard screenshots (`docs/DEMO.md`),
final report `docs/REPORT.md` (9-12 Oct), Canva deck (13-17 Oct), rehearsal with live demo (18-21 Oct). Review: 22 Oct.
