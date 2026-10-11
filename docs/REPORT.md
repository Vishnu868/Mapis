# MAPIS — Multi-Agent Prompt Injection Shield: Final Report

Team A1: Dodla Nithya Sai, Vishnu Vardhan, Sreekar Reddy, Beena Reddy. Supervisor: Prof. Sripriyan. Final review: 22 October 2026.

All numbers below were measured and come from `results/` (mirrored in Drive `mapis_results`). `CLAUDE.md` sections 4m–4q hold the full record.

## 1. Problem and idea

In a multi-agent LLM pipeline, an injected instruction can travel across agents. Attacks can also be split into fragments that look harmless message by message (a changed destination in one document, an "authority" sentence in another, then an agent action that uses both). A stateless guardrail judges each message alone and cannot tell such an action from one the user asked for.

MAPIS is a stateful, trust-scoring monitor on the communication layer. Every message, tool call, tool output and memory read/write passes through a FastAPI tap. A fine-tuned transformer scores each event against the accumulated session state (trust 0 = malicious, 1 = safe).

## 2. System

- **Tap and testbed.** FastAPI `POST /inspect`. A deterministic 5-agent testbed (planner, web, file, memory, code/email) runs on LangGraph and AutoGen 0.2.
- **Session state.** `backend/core/session.py` is shared by the runtime and the training-data builder. It tracks goal, untrusted cues, authority claims, tainted indicators (emails, URLs, IBAN-like ids, fragments), trusted items and per-agent baselines.
- **Four signals.** Instruction-in-data, drift from the user goal (state-changing actions only), cross-hop provenance and escalation, behavioural anomaly.
- **Model.** DeBERTa-v3-small, temperature-calibrated. The event text goes first, then a one-line signal summary, then the session history. Long events are chunked and the minimum trust is taken. Noisy-OR fusion with the rule signals.
- **Tiered response.** PASS ≥ 0.75, FLAG 0.50–0.75 (raises session sensitivity), QUARANTINE 0.25–0.50 (held), BLOCK < 0.25 (dropped, channel suspended), with a forensic trace origin → relay → action. Dashboard in `frontend/` (live monitor, session inspector, results).
- **Evasion defences.** `canonical()` normalises Unicode, zero-width characters, `hxxp`, `[.]`, "at/dot" spellings and grouped IBANs. Fragment matching assembles items split across hops.

## 3. Data (MAPIS-Bench)

| Set | Content |
|---|---|
| v1 | 1,693 sessions from AgentDojo and InjecAgent, audited against the sources |
| BIPIA | 1,800 minimal-pair sessions; the BIPIA test split was never trained on |
| Decomposed | 288 invisible-per-message exfiltration sessions (evaluation only) |
| MultiHop | Fragment attacks in real carrier text across 4 skeletons (the abstract's mechanisms), depth 0/2/4. Every attack has matched benign twins: authorized, resisted, designated |
| RealHarm | InjecAgent direct harm and ASB, with unseen attacker tools and agents |
| Adaptive | 1,692 sessions of evasive attacks: obfuscated, split, unicode, paraphrase, long delay, combo |

Test families, phrasings and tools are held out. The final test has 2,304 sessions, including 576 Adaptive sessions (192 attacks).

## 4. Results

### 4.1 Headline (session level, 2,304 held-out sessions, mean ± std over 3 training seeds)

| System | Recall | FPR | Accuracy |
|---|---|---|---|
| **MAPIS** | **97.7 ± 0.6 %** | **0.5 ± 0.4 %** | **98.5 ± 0.3 %** |
| Stateless DeBERTa (same data, event only) | 94.6 ± 0.4 % | 35.2 ± 2.1 % | 81.4 ± 1.1 % |
| Llama Guard 3-1B | 86.1 % | 90.3 % | 52.3 % |
| ProtectAI deberta-v3 injection v2 | 53.3 % | 49.5 % | — |
| Prompt Guard 2 (86M) | 7.5 % | 0.1 % | — |

MAPIS per set (recall / FPR):
- Multi-hop: 100 % / 2.2 ± 2.3 % (per seed 1.2 / 5.3 / 0.0).
- Adaptive: 100 % / 0.0 %, on all six techniques and all seeds.
- InjecAgent direct harm: 99.5 % / 0 %. ASB: 100 % / 0 %.
- Decomposed: 100 / 0. v1: 100 / 0.
- BIPIA (never trained on): 95.1 % / 0.7 %.

### 4.2 Stateless detection at a matched false-positive budget

At the default threshold the stateless model buys 92 % multi-hop recall with a 55 % FPR, because it flags the user-authorized twins. Holding it to ≤ 5 % FPR (threshold chosen on validation, applied to test; 3-seed means):

| Set | Stateless recall | MAPIS recall |
|---|---|---|
| Multi-hop | 6.7 % | 100 % |
| Adaptive | 8.7 % | 100 % |
| InjecAgent-DH | 90.7 % | 99.5 % |
| ASB | 98.3 % | 100 % |

On multi-hop and adaptive attacks the gap is about 93 and 91 points, against the target of ≥ 20. The thresholds picked on validation did not hold exactly on test (seed 3 multi-hop FPR 7.7 %, seed 2 adaptive 8.8 %), so these stateless recalls are generous to the baseline. On RealHarm the explicit injection text makes message-level detection competitive, and the gap is ≤ 9 points.

### 4.3 LLM-based baselines (153 class-balanced sessions, up to 20 per dataset)

| System | Recall | FPR | Accuracy |
|---|---|---|---|
| **MAPIS** | **100 %** | **0.0 %** | **100 %** |
| Stateless DeBERTa | 91.2 % | 32.9 % | 79.7 % |
| History-aware LLM judge (qwen2.5:7b, whole transcript) | 67.5 % | 23.3 % | 71.9 % |
| NeMo Guardrails self-check input rail (qwen2.5:7b) | 48.7 % | 17.8 % | 64.7 % |

The judge finds the multi-hop attacks but flags 80 % of the benign multi-hop twins. NeMo misses most multi-hop and adaptive attacks. Neither separates an attack from the identical user-authorized action. With n = 20 per dataset, a 0 % FPR cell has a 95 % upper bound of about 5 %, so §4.1 is the headline and this table is the like-for-like comparison. The judge and NeMo checker are a 7B local model.

### 4.4 Live LLM agents (AgentDojo v1.2.1, qwen2.5:7b, 4 suites, 39 benign + 144 attacked runs per defence)

| Defence | Utility, no attack | Utility under attack | Attack success rate |
|---|---|---|---|
| none | 28.2 % | 22.9 % | 15.3 % (22/144) |
| MAPIS | 25.6 % | 15.3 % | 0.0 % (0/144), 95 % upper bound 2.6 % |
| stateless DeBERTa | 20.5 % | 16.0 % | 0.0 % (0/144) |

MAPIS removed all 22 successful attacks at a cost of 1 of 39 benign tasks. AgentDojo injections are explicit text in tool outputs, so a message-level detector also stops them. This run shows MAPIS working inside a live agent pipeline; it does not separate MAPIS from the stateless model (§4.2 does).

### 4.5 Cost

63.0 ms per event single and 51.4 ms batched on an RTX 3050 laptop GPU (`results/evaluate.json`), against the 200 ms target.

### 4.6 Targets

| Target | Result |
|---|---|
| Accuracy ≥ 90 % | 98.5 % |
| FPR ≤ 5 % | 0.5 % overall; multi-hop mean 2.2 % (one seed 5.3 %) |
| < 200 ms per message | 63 ms |
| ≥ 20 points recall gain on multi-hop | +93 points at matched FPR (+7.7 at the default threshold) |

## 5. Limits

- MultiHop and Adaptive are template-generated (held-out families, phrasings and tools; real carrier text). The team's independent hand-written set (`docs/INDEPENDENT_TESTSET_GUIDE.md`) is the remaining external check.
- Seed 2 multi-hop FPR is 5.3 % [3–10], marginally above the 5 % target. The 3-seed mean is below it.
- MAPIS was trained on AgentDojo-style injections, which the live run also uses.
- The live agent is a 7B local model (28 % benign utility). The LLM judge and NeMo ran on the same 7B model.
- On single-hop BIPIA there is no cross-hop evidence, so stateless recall is within seed variance of MAPIS.
- Related work already covers parts of this space (Prompt Infection, G-Safeguard, LlamaFirewall AlignmentCheck). MAPIS's contribution is the combination: a small classifier with stateful session signals at a framework-agnostic tap, fragment attacks with matched benign twins, a provenance trace and a tiered response.

## 6. Reproduction

`CLAUDE.md` §6 and `NEXT_STEPS.md` have the exact commands. In short: `.\scripts\run_pipeline.ps1 -Seeds 3`, then `python scripts/stateless_sweep.py`, `.\scripts\run_pipeline.ps1 -Live` and `-LLMBaselines`. Tests: `python -m pytest -q` (29 tests).
