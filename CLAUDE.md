# MAPIS — working rules and core idea (read this first, every session)

Owner: Vishnu Vardhan (team A1: Nithya Sai, Vishnu Vardhan, Sreekar Reddy, Beena Reddy; supervisor Prof. Sripriyan). B.Tech final-year project.

## The core idea (from the Zeroth and First Reviews) — this is THE goal
MAPIS = a **stateful, trust-scoring monitor on the communication layer of a multi-agent LLM pipeline** that stops **indirect prompt injection that
spreads across agent hops**, including attacks split into fragments that look harmless message-by-message (which stateless guardrails —
Llama Guard, NeMo — cannot see because the evidence is in the session history, not in the message).
Required components: FastAPI tap on every agent message / tool call / tool output / memory read+write; per-channel rolling session store (Redis);
four signals — semantic drift from the user goal, instruction-in-data analysis, cross-hop pattern correlation (provenance of untrusted content),
behavioural anomaly; a fine-tuned transformer classifier that scores each message **against the accumulated session state** -> trust 0..1
(0 = malicious, 1 = safe); four-tier response PASS >=0.75 / FLAG 0.50-0.75 / QUARANTINE 0.25-0.50 / BLOCK <0.25 with channel suspension;
forensic propagation trace (origin -> relay -> action); live dashboard; testbed on AutoGen AND LangGraph (web, code, file, memory agents);
MAPIS-Bench multi-hop dataset, five attack classes; evaluation vs Llama Guard / NeMo Guardrails (stateless) on identical events.
Targets: >=90% accuracy, <=5% FPR, <200 ms per message, >=20 points recall gain over stateless detection on MULTI-HOP attacks.

The Project Abstract (owner-supplied HTML) is the plan of record: five attack MECHANISMS (document poisoning, memory injection, tool-output manipulation,
cross-agent instruction injection, goal hijacking), 5 phases, seven metrics (accuracy, precision, recall, F1, FPR, latency, computational overhead), compared with
Llama Guard and NeMo across attack types and pipeline depths. MAPIS-MultiHop tags every session with its mechanism (`attack_vector`) and extra-hop depth.

## Rules the owner set (follow them)
1. Deliver the core idea for real. Do not water it down, do not substitute side projects, do not spend effort on results that are not the main goal
   (e.g. extra baselines, tuning tangents).
2. Do NOT hedge the work or hand over "what to say to the viva panel". Finish the implementation so it stands on its own; state limits briefly and factually, once.
3. The comparison with Llama Guard / NeMo is part of the plan and is reported as run. Do not undermine it with excuses.
4. Honesty still applies to numbers: never fabricate or inflate results; report what was measured.
5. Training/GPU runs happen on a friend's RTX 3050 laptop (Windows, PowerShell, venv `mapis`); the owner relays outputs. Results are shared through the Google Drive
   folder `mapis_results`. The cloud sandbox cannot reach huggingface.co.
6. Work on branch `claude/inspiring-hopper-4gqkjy` (PR #1). The deck will be finished at the end in Canva (connector to be added later).

7. Whenever asking the owner to upload to Drive `mapis_results`, list the exact files every time:
   results\benchmark.json, results\benchmark_llamaguard.json, results\evaluate.json (if present), results\logs\ (whole folder),
   artifacts\mapis_detector\{calibration.json, history.json, training_config.json}, artifacts\mapis_stateless\{calibration.json, history.json}.
   Never the model weights (*.safetensors).

## Repo map
backend/core (shield, features, context, store, detector) · backend/ml (train / evaluate) · backend/agents (testbed + LangGraph tap) ·
scripts/ (prepare_phase4_training_data.py, benchmark.py, generate_decomposed.py, dataset_build/) · docs/STATUS.md (measured results) · docs/TRAINING.md (GPU commands).
