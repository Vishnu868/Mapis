# MAPIS status (verified in this repository)

## Implemented and tested (pytest, no GPU needed)
- Four-tier response PASS / FLAG / QUARANTINE / BLOCK on the 0=malicious scale, channel suspension, quarantine review API.
- Session store: Redis with in-memory fallback; bounded window; goal vector text never overwritten by agent output.
- Four stateful signals + noisy-OR fusion + session sensitivity; forensic propagation trace (origin → relay → action).
- 5-agent testbed over a simulated environment (web / files / memory / email) on BOTH LangGraph (`backend/agents/graph.py`) and AutoGen 0.2 (`backend/agents/autogen_testbed.py`, tap via `process_message_before_send`); tap on every hop incl. memory writes/reads and tool calls; `POST /pipeline/run {"framework": "autogen"}`.
- Stateful classifier input (v4): `backend/core/session.py` turns the Redis session state into SESSION SIGNALS (drift, instruction cues, authority claims, cross-hop item reuse, user-supplied items, behaviour) + abbreviated history; the live shield and the dataset builder call the same code (parity is unit-tested), so the transformer is trained on the evidence it sees at runtime.
- MAPIS-MultiHop benchmark (`scripts/generate_multihop.py`, 1,404 sessions, 5 attack classes): attacks assembled from declarative fragments across untrusted hops (no imperative command in any single message), with authorized / resisted / designated benign twins; split by family and phrasing pool.
- FastAPI tap, SQLite forensic log, WebSocket push, React dashboard (timeline, alerts, traces, quarantine review).
- Training / calibration (temperature) / evaluation code; train/serve text parity is unit-tested.

## FINAL RESULTS — 3-seed run (6 Oct 2026, commit 40d8975, seeds 42 + 2 extra, 1,728 test sessions) — THE NUMBERS TO PRESENT (supersede run 3 below)
Source: Drive `mapis_results` -> results\seeds\summary.json (mean +/- std over 3 training seeds) and results\logs\7_benchmark.txt (seed 42, Wilson 95 % CIs).

| System (session level, 1,728 held-out sessions) | Recall | FPR | Accuracy | F1 |
|---|---|---|---|---|
| **MAPIS, 3-seed mean** | **97.1 +/- 1.5 %** | **0.5 +/- 0.3 %** | **98.0 +/- 0.9 %** | 0.984 +/- 0.007 |
| MAPIS seed 42 | 98.4 % [98-99] | 0.9 % [0-2] | 98.7 % | 0.989 |
| MAPIS learned model only, seed 42 | 98.4 % | 0.8 % | 98.7 % | 0.990 |
| Stateless DeBERTa (same data, event only), 3-seed mean | 92.8 +/- 1.2 % | 17.6 +/- 1.6 % | 89.0 +/- 0.2 % | 0.914 |
| Llama Guard 3-1B (run A, same test events) | 83.6 % | 84.4 % | 58.6 % | - |
| Regex | 14.6 % | 0.0 % | 46.0 % | 0.255 |

**Multi-hop (MAPIS-MultiHop test, 65 attacks / 169 benign twins):** MAPIS **100 +/- 0 % recall, FPR 0.6 +/- 0.8 %** (seed 42: 100 % / 1.8 %, authorized 2.3, resisted 0, designated 0; seeds 2 and 3: 100 % / 0.0 %);
stateless 50.3 +/- 7.4 % / 21.5 +/- 4.3 % (seed 42: 56.9 % / 24.9 %, flags 75 % of authorized twins); Llama Guard 100 % / 100 % (flags everything); regex 0 / 0.
**Recall gain over stateless on multi-hop: +49.7 points (3-seed mean), with an FPR 21 points lower.**
Per mechanism seed 42 (MAPIS / stateless): goal hijacking 100 / 60, cross-agent 100 / 78, tool-output 100 / 97, memory 100 / 88, document 100 / 100 (n=3) — counted over multihop + realharm attacks.
RealHarm (real attack corpora, unseen attacker tools/agents): MAPIS 100 % / 0 % on InjecAgent-DH and ASB, all seeds; stateless 100 % recall but **50 % FPR on InjecAgent-DH** (it cannot tell the user-authorized twin from the attack).
Decomposed: MAPIS 100 % / 0 %; stateless 8.3 %. v1: 100 % / 0 of 23 benign. BIPIA (never trained on): MAPIS 94.7 +/- 2.7 % / 1.2 +/- 0.2 % (seed 42: 97.2 / 1.5); stateless 95.8 +/- 0.9 / 2.0 +/- 0.4.
Missed attacks seed 42: 0 of 213 multi-hop/realharm/decomposed attacks; v1 benign: 0 flagged. Latency (run v3, same architecture): 66 ms/event single, 51.6 ms batched on the RTX 3050.
**All four targets met with seed stability:** accuracy 98.0 % (>= 90), FPR 0.5 % (<= 5; multi-hop 0.6 %), latency 66 ms (< 200), multi-hop recall gain +49.7 points (>= 20).
Honest notes: on BIPIA (single-hop, no cross-hop evidence) stateless recall is ~1 point higher and within seed variance, at higher FPR; MultiHop is template-generated (held-out families, phrasings,
tools; real carriers) -> the team's independent set is the remaining external check; NeMo not run yet; Llama Guard numbers are from run A on identical test events (not re-run on this model, it does not depend on it).

## Evaluation upgrade (6 Oct) - implemented, laptop runs pending
See CLAUDE.md section 4h. MAPIS-Adaptive (evasive attacker, held-out styles), canonical/fragment provenance matching, Prompt Guard 2 / ProtectAI /
history-aware LLM judge / NeMo baselines on any OpenAI-compatible endpoint, live LLM agents on AgentDojo with MAPIS tapping every message.
Sandbox rules-only check on MAPIS-Adaptive test (576 sessions): recall 51 % -> 83 % with canonical/fragment matching, 0 false positives before and after.

## Earlier results - run 3 (commit 7da86d4, RTX 3050, DeBERTa-v3-small, 2 epochs; results/benchmark.json in Drive mapis_results)
Session level, 1,364 held-out test sessions, every system sees the same events in the same order, 95 % Wilson intervals.

| System | Recall | FPR | Accuracy | F1 |
|---|---|---|---|---|
| **MAPIS (stateful DeBERTa + session signals + rules)** | **94.4 %** [92.7-95.7] | **1.7 %** [0.8-3.4] | **95.6 %** | 0.967 |
| MAPIS learned model only (no rule backstop) | 93.3 % | 1.7 % | 94.9 % | 0.962 |
| Stateless DeBERTa (same data, current event only) | 89.9 % | 10.3 % | 89.9 % | 0.925 |
| Llama Guard 3-1B (stateless) | 81.4 % | 82.8 % | 61.7 % | 0.746 |
| Regex | 16.9 % | 0.0 % | 42.4 % | 0.290 |

**Multi-hop attacks (MAPIS-MultiHop test: 65 attacks from held-out families, 169 matched benign twins)**

| System | Attack recall | FPR | Benign twins flagged (authorized / resisted / designated) |
|---|---|---|---|
| **MAPIS** | **100 %** (65/65) [94.4-100] | **3.0 %** (5/169) | 1/65, 3/65, 1/39 |
| Stateless DeBERTa | 63.1 % (41/65) | 24.3 % (41/169) | 37/65, 3/65, 1/39 |
| Llama Guard 3-1B | 100 % | 100 % (flags every session) | 65/65, 65/65, 39/39 |
| Regex | 0 % | 0 % | - |

- Recall gain over the stateless model on multi-hop attacks: **+36.9 points** (target >= 20), with an FPR 21 points lower.
- Per mechanism (MAPIS / stateless): tool-output manipulation 100 / 25 %, goal hijacking 100 / 100 %, cross-agent injection 100 / 53 %, memory injection 100 / 91 %, document poisoning 100 / 0 % (n=2).
- Per pipeline depth (0 / 2 / 4 extra hops): MAPIS 100 / 100 / 100 %; stateless 72 / 58 / 54 % - the stateless model degrades as the attack is spread over more hops.
- Event level (2,134 multi-hop events): stateful 82.1 % recall / 0.1 % FPR vs stateless 44.6 % / 2.4 %.
- Other sets (MAPIS): MAPIS-Bench v1 100 % recall, 0/26 benign flagged; Decomposed 100 % (learned model alone 58 %, the cross-hop provenance rule supplies the rest; stateless 0 %); BIPIA (never trained on) 91.2 % / 1.0 %.
- Per class (all test sets, MAPIS): exfiltration 99.3 %, financial 100 %, code/tool 98.6 %, instruction override 89.6 % (misses are BIPIA "harmless-looking request" injections), physical safety 100 %.
- Cost: 60.5 ms per event single, 49.6 ms batched on the RTX 3050 (target < 200 ms); 22 ms mean / 59 ms p95 per event inside the full shield; 85 CPU-ms per event including the detector.

Targets: accuracy >= 90 % -> 95.6 %; FPR <= 5 % -> 1.7 % (multi-hop 3.0 %); latency < 200 ms -> 61 ms; >= 20-point multi-hop recall gain over stateless -> +36.9. All met.
Limits: the multi-hop benchmark is template-generated (held-out families, phrasings and carriers, real BIPIA carrier text); its benign set is 169 sessions, so the FPR interval is 1.3-6.7 %.
NeMo Guardrails is not run (needs an LLM API key).

## History: run 1 of the state-aware model (v4 data, RTX 3050, session level, 1,364 test sessions, 95 % Wilson intervals in results/benchmark.json)
| System | Recall | FPR | Accuracy |
|---|---|---|---|
| MAPIS (stateful DeBERTa) | 93.3 % | 2.1 % | 94.7 % |
| Stateless DeBERTa (same data, event only) | 89.2 % | 7.9 % | 90.1 % |
| Llama Guard 3-1B | 81.4 % | 82.8 % | 61.7 % |
| Regex | 16.9 % | 0.0 % | 42.4 % |

MAPIS-MultiHop only (65 attack / 169 benign sessions): MAPIS 60.0 % recall / 2.4 % FPR; stateless DeBERTa 40.0 % / 17.8 % (flags 40 % of sessions where the user named the destination); Llama Guard 100 % / 100 % (flags every session); regex 0 % / 0 %.
Decomposed set: MAPIS 100 %, stateless 0 %. BIPIA (never trained on): MAPIS 93.8 % / 2.5 %. Latency 61 ms per event.
Failure analysis of run 1: all 26 missed multi-hop attacks were instruction-override (13/13) and physical-safety (13/13); the three classes where an item travels across hops (exfiltration, financial, code) were caught 100 %.
Cause: nothing travels in those attacks - an untrusted document claims a waiver, then the agent takes an action the user never asked for - and the session signals did not express that, so the model memorised training tool names.
Fix (applied in run 3): new tool-agnostic session signals `unrequested_action` and `claim_echo`, an escalation term in the cross-hop correlation signal, drift only for state-changing calls, URL host matching, more training families for override / physical.

## Earlier measurement, v3 model without session signals (RTX 3050, commit edd7584; the v4 retrain replaces these numbers); DeBERTa-v3-small, 2 epochs, best epoch by validation F1 at FPR <= 5 %)
Event-level (long events are scored chunk-wise, trust = min over chunks), threshold trust < 0.5, 95 % Wilson intervals.

| Held-out split | Events | Recall | FPR | TF-IDF+LogReg baseline (recall / FPR) | Stateless DeBERTa (recall / FPR) |
|---|---|---|---|---|---|
| `test` (unseen sessions) | 217 mal / 251 safe | 100 % [98.3-100] | 1.6 % [0.6-4.0] | 99.5 % / 0 % | 100 % / 0 % |
| `test_ood` (unseen attack templates) | 285 / 244 | 100 % [98.7-100] | 0.8 % [0.2-2.9] | 100 % / 0 % | 100 % / 2.9 % |
| `test_bipia` (a different dataset, never trained on) | 600 / 400 | 95.0 % [93.0-96.5] | 0.5 % [0.1-1.8] | 81.0 % / 12.0 % | 92.7 % / 1.0 % |

- The only split that separates models is BIPIA: DeBERTa beats a bag-of-words baseline by +14 points recall and -11.5 points FPR on a dataset it never saw. On AgentDojo / InjecAgent every model scores ~100 %.
- Stateful vs stateless on BIPIA: +2.3 points recall (570 vs 556 of 600); the intervals touch, so call it "a small gain", not a proven one.
- Weak spots (BIPIA, per attack category): injections that look like harmless requests are missed most - Sentiment Analysis 74 %, Conversational Agent 76 %, Research Assistance 80 %, Task Automation 85 %.
  The model is confidently wrong on them (trust ~0.99): an embedded "What movies are playing this weekend?" has no malicious content, only irrelevance to the user's task.
- Classifier latency on the 3050: 55 ms per event (single), 46 ms per event batched - inside the 200 ms budget.
- Session-level benchmark (test sessions): MAPIS recall 96.6 %, FPR 0.8 % overall; MAPIS-Bench v1 benign 0/26 flagged; decomposed attacks 100 % with provenance vs 0 % without it and 0 % for the stateless model.
- Temperature calibration: 1.285 (stateful), 1.409 (stateless).

## Comparison with a general safety guardrail (Llama Guard 3-1B, same events, session level, 95 % intervals)
| System | Recall | FPR | v1 benign FPR | Decomposed FPR | BIPIA recall / FPR |
|---|---|---|---|---|---|
| MAPIS (stateful DeBERTa + signals) | 96.6 % | 0.8 % | 0 % (0/26) | 0 % | 95.0 % / 1.0 % |
| Llama Guard 3-1B (stateless) | 80.0 % | 71.2 % [65-76] | 88.5 % | 100 % (flags every session) | 72.5 % / 65.5 % |

Read with care: Llama Guard is a *content-safety* classifier (violence, privacy, crime...), not a prompt-injection detector, so applying it to injection detection is a category mismatch.
It flags ordinary agent traffic that mentions emails, accounts or payments, and a session is "held" when ANY event is flagged, which compounds per-event noise over long sessions.
A fairer baseline is Meta's dedicated Llama Prompt Guard 2 (adapter added: `--systems promptguard`, not yet run). NeMo Guardrails is not run (needs an LLM key).

## NOT yet measured / not done
- Llama Prompt Guard 2 and NeMo Guardrails (adapters written; Prompt Guard needs gated access, NeMo needs an LLM key).
- Fusion weights and tier thresholds are defaults; no tuning beyond the classifier's 0.5 boundary.
- Full-shield latency including Redis, and the dashboard against the trained model.
- v4 retrain (stateful with session signals vs stateless) and the MAPIS-MultiHop numbers: produced by `scripts/run_pipeline.ps1` on the GPU laptop.

## Dataset audit (done against the original sources where available)
- InjecAgent: 544 attack sessions match `test_cases_ds_base.json` exactly (user instruction, tool response, attacker instruction; 32 distinct instructions). Only the data-stealing (ds) cases are used; the 510 direct-harm (dh) cases are not.
- AgentDojo: all 1,132 sessions (1,000 attack + 132 benign) match the original `runs/` files exactly (message count, role, content, suite / task / attack metadata; 0 mismatches,
  0 missing files). No benign session contains the injection tag, no duplicate sessions, zero split leakage by (suite, user task).
- Composition caveats (true, but not errors): the 132 benign AgentDojo sessions are 97 normal user tasks + 35 AgentDojo *injection goals run as the user's own request*
  (tagged `benign_kind`; all 35 landed in train). Sessions come from three models (gpt-4o 927, claude-3.5 122, claude-3.7 83). 617 of the 1,000 attacks did not succeed
  (the agent resisted); they still contain the injection, so they are valid detection samples. Injection payloads repeat across splits (88 of 160 test payloads also occur in
  train after whitespace normalisation), hence the held-out-template `test_ood` split.
- Benign data is thin: 26 test sessions (23 independent AgentDojo tasks + 3 InjecAgent). One false positive = 3.8 %, and the 95 % interval of "1 in 26" is 0.7 %-18.9 %.
  Benchmarks therefore print Wilson 95 % intervals; do not quote a bare FPR.
- Class labels were wrong in v1 (all 910 important_instructions / tool_knowledge attacks were 'financial_manipulation', decided from banking tasks only). Remapped by (suite, injection task)
  with `scripts/dataset_build/remap_agentdojo_classes.py`; originals kept in `original_mapis_attack_class`. Corrected attack classes: data_exfiltration 981, code_tool_manipulation 382,
  instruction_override 82, financial_manipulation 63, physical_safety_harm 18, unclassified 18 (total 1,544). The old per-class counts on the First Review slides are wrong.

## Training-data fixes found by auditing (all measured on the real files)
- Truncation bug: the old text put the scored event LAST and the tokenizer cut at 384 tokens, so for 83 % of AgentDojo malicious events the injection lay beyond the budget (the model could not see it).
  Now the scored event comes first, context is abbreviated, long events are split into overlapping 900-char chunks, trust = min over chunks, and chunk labels use the known injection span
  (the chunk containing it is positive, other chunks of the same event are hard negatives). Unit-tested.
- BIPIA (email / table / code, 1,800 minimal-pair sessions) added: its train part is used for training, its test part (unseen contexts AND unseen attack categories) is `test_bipia`, never trained on.
  PINT (only 8 public example rows) and ASB (tool / task definitions, no trajectories) were evaluated and not used.

## Known limits to state openly
- MAPIS-Bench v1 labels the injection-bearing *tool event*; most attacks there are single-injection, so v1 alone cannot show a
  stateful advantage. `scripts/generate_decomposed.py` builds template-seeded decomposed attacks (split by template family) for that.
  It is synthetic and was written around the provenance mechanism, so results on it demonstrate the mechanism, not real-world recall.
- Phase-4 v1 labels were shortcut-prone (measured on the real data: a role-only rule scored 89.4 % accuracy / 100 % recall / 34.8 % FPR; every AgentDojo attack carries a literal
  `<INFORMATION>` tag; InjecAgent had no benign tool responses). v2 fixes this: tags stripped everywhere, 717 clean pre-injection AgentDojo tool outputs and 544 InjecAgent
  minimal-pair "clean twins" as hard negatives (synthetic neutral filler, disjoint per split), and a template-held-out `test_ood` split. Role-only now scores 0 % recall.
- Even so, on v2 a TF-IDF + logistic regression scores ~98 % (test) and ~100 % (test_ood): injected instructions are blatantly imperative in these benchmarks. Single-event
  accuracy cannot demonstrate an advantage; the decomposed multi-hop benchmark is where the stateful claim has to be shown.
- A false-positive audit found three kinds of artefact, all fixed: a regex cue matching the word 'email' next to an address; a 27k-character benign listing (61 chunks, min-pooling gives many chances to misfire);
  and the model memorising the document text that precedes AgentDojo injections (fixed with nearest-negative and shifted-window training rows and by removing the chunk-position header).
- Provenance can false-positive when a legitimate destination comes from a tool result (e.g. "pay the bill in the file").
  Sources the user explicitly named in the task (e.g. the file in 'pay the bill in bill.txt') are trusted origins; anything else lands in QUARANTINE
  for a human. The remaining false-positive cost is measured on the benign sessions in the benchmark.
- Fusion weights are defaults; tune on validation before the final review.
- AutoGen is not implemented (LangGraph only).
