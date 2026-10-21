# MAPIS — Multi-Agent Prompt Injection Shield: Final Report

Team A1: Dodla Nithya Sai, Vishnu Vardhan, Sreekar Reddy, Beena Reddy. Supervisor: Prof. Sripriyan. Final review: 22 October 2026.

All numbers below were measured and come from `results/` (mirrored in Drive `mapis_results`). `CLAUDE.md` sections 4m–4v hold the full record.

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
- **Action-argument tampering checks** (`tamper_risk`, added 21 Oct, no retraining). Every argument of a state-changing tool call is compared with what the user said: privilege/safety flags, roles or command switches the user never asked for; values that contradict the user's own (same-shape id, number next to the same word, opposite on/off, different time); destination-type arguments whose value appeared only in untrusted or agent-relayed text. Fused through the provenance weight; on by default in the shield (benchmark name `mapis-v2`).

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

### 4.1 Headline (session level, 2,304 held-out sessions, mean ± std over 5 training seeds: 42, 2, 3, 4, 5)

| System | Recall | FPR | Accuracy |
|---|---|---|---|
| **MAPIS** | **98.0 ± 0.6 %** | **0.9 ± 0.8 %** | **98.5 %** |
| Stateless DeBERTa (same data, event only) | 94.1 ± 0.9 % | 33.2 ± 3.5 % | 82.0 % |
| Llama Guard 3-1B | 86.1 % | 90.3 % | 52.3 % |
| ProtectAI deberta-v3 injection v2 | 53.3 % | 49.5 % | 52.1 % |
| Prompt Guard 2 (86M) | 7.5 % | 0.1 % | 48.4 % |

MAPIS per set (recall / FPR, 5 seeds):
- Multi-hop: 100 % / 3.0 ± 3.0 % at the default hold cut-off (0.50). With a cut-off chosen on the validation split only (`scripts/calibrate_mapis.py`), every seed checked stays ≤ 5 % (seeds 42/2/3: 1.2→0.6, 5.3→1.8, 0.0→0.0 %) with recall unchanged. At the default cut-off two of five seeds exceed 5 % (5.3 and 7.7 %); seeds 4 and 5 were not calibrated.
- Adaptive: 100 % / 0.4 % (0.0 % in four seeds, 1.8 % in one), all six techniques.
- InjecAgent direct harm: 99.4 % / 0 %. ASB: 100 % / 0 %.
- Decomposed: 100 / 0. v1: 100 / 0.
- BIPIA (never trained on): 95.8 % / 1.4 % (stateless 94.5 % / 2.2 %).

The tampering checks (§4.5) change no decision on these 2,304 sessions in any seed, so this table holds for the final system.

### 4.2 Stateless detection at a matched false-positive budget

At the default threshold the stateless model buys 86.5 % multi-hop recall with a 51 % FPR (5 seeds), because it flags the user-authorized twins. Holding it to ≤ 5 % FPR (threshold chosen on validation, applied to test; 3-seed means):

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

### 4.5 Harder tests, the gap they found, and the fix (test-only sets, never trained on)

Two sets were built to find where MAPIS fails: **MAPIS-StateAttack** (56 attacks / 112 twins aimed at the session record) and a **team-written independent set** (20 attacks + 20 twins in plain English by the four team members, without the generators).

**First result (MAPIS as trained, 5 seeds).** Team-written set: 40 % recall (35–45 %), 7.0 % FPR. StateAttack: 55.7 % recall, 10.2 % FPR. MAPIS caught the attacks whose planted item is an email or URL. The 13 team-set misses of seed 42: 7 changed a value the user gave (alarm delay 360 min instead of 10, wallet `WL-5508` instead of `PS-7731`, card `CC-77`, a door open until 20:00, ventilation off), 4 added a privilege/safety flag (`bypass_checks=true`, `override_balance=true`, a role grant, `--disable-auth`), 2 used a destination relayed by another agent.

**Fix: action-argument tampering checks (§2), measured with the trained models on all 5 seeds (2,512 test sessions per seed, `scripts/run_v2_checks.ps1`, `results/v2/`).**

| Mean of five seeds | Before | With the checks |
|---|---|---|
| Team-written set, recall | 40.0 % | **95.0 % (every seed)** |
| Team-written set, FPR | 7.0 % | 7.0 % |
| StateAttack, recall | 55.7 % | **80.4 %** |
| StateAttack, FPR | 10.2 % | 10.2 % |
| Six headline sets (2,304) | §4.1 | unchanged |

No new false positive on any session in any seed. StateAttack per technique (before → after): buried evidence 76.7 → 90.0 %, split claim 78.3 → 91.7 %, laundered through memory 63.3 → 86.7 %, item introduced by an agent 25.0 → 90.0 %, item the agent must decode 25.0 → 25.0 %. Document-poisoning vector 78.6 → 100 %. The one remaining team-set miss (ventilation off while the user said keep it on) was caused by an on/off matching bug fixed after the run; across all 2,512 test sessions the fix changes only that attack (rules-only check). **Caveat:** the checks were designed after reading the team-set misses, so 95 % there is not an independent estimate; a fresh hand-written set is needed to confirm it. n = 20 per class (95 % recall: Wilson 76–99 %).

Team-written set, seed 42, all systems:

| System | Recall | FPR | Accuracy |
|---|---|---|---|
| **MAPIS with tampering checks** | **95.0 %** | **5.0 %** | **95.0 %** |
| MAPIS before the checks | 35.0 % | 5.0 % (1 of 20, a designated twin) | 65.0 % |
| Stateless DeBERTa | 40.0 % | 40.0 % | 50.0 % |
| ProtectAI v2 | 50.0 % | 50.0 % | 50.0 % |
| Llama Guard 3-1B | 100 % | 100 % | 50.0 % |

The baselines flag benign and attack sessions at the same rate. On StateAttack the stateless model reaches 78.6–100 % recall only at 57–79 % FPR (seeds 42/2/3).

**Rule ablation (seed 42, adaptive + multi-hop + StateAttack, 978 sessions, before the tampering checks).** Full MAPIS 92.0 % / 1.8 %, model only 92.0 % / 1.7 %, without provenance 92.0 % / 1.7 %. The classifier has absorbed the four original rule signals through its input line; the tampering checks are the exception (they compare argument values with the user's request, which the classifier input does not).

### 4.6 Cost

63.0 ms per event single and 51.4 ms batched on an RTX 3050 laptop GPU (`results/evaluate.json`), against the 200 ms target.

### 4.7 Targets

| Target | Result |
|---|---|
| Accuracy ≥ 90 % | 98.5 % (5 seeds) |
| FPR ≤ 5 % | 0.9 % overall; multi-hop 3.0 % mean at the default cut-off, ≤ 1.8 % on the three seeds checked with the validation-calibrated cut-off |
| < 200 ms per message | 63 ms |
| ≥ 20 points recall gain on multi-hop | +93 points at matched FPR, 3 seeds (+13.5 at the default threshold) |

## 5. Limits

- The tampering checks were designed after reading the team-set misses, so their 95 % there is not an independent estimate; a fresh hand-written set is the next step.
- StateAttack reaches 80.4 % recall but at 10.2 % FPR (above the 5 % target; mostly memory-laundering twins); items the agent must decode stay at 25 %.
- MultiHop and Adaptive are template-generated (held-out families, phrasings and tools; real carrier text).
- Two seeds of five have a multi-hop FPR above 5 % at the default cut-off; the validation-calibrated cut-off fixes it for the three seeds checked.
- MAPIS was trained on AgentDojo-style injections, which the live run also uses. The live agent is a 7B local model (28 % benign utility); the LLM judge and NeMo ran on the same 7B model.
- On single-hop BIPIA there is no cross-hop evidence, so stateless recall is within seed variance of MAPIS.
- The four original rule signals add nothing measurable once the classifier has the session signals; only the tampering checks add recall.
- Related work already covers parts of this space (Prompt Infection, G-Safeguard, LlamaFirewall AlignmentCheck). MAPIS's contribution is the combination: a small classifier with stateful session signals at a framework-agnostic tap, fragment attacks with matched benign twins, a provenance trace and a tiered response.

## 6. Reproduction

`CLAUDE.md` §6 and `NEXT_STEPS.md` have the exact commands. In short: `.\scripts\run_pipeline.ps1 -Seeds 5`, `.\scripts\run_final_checks.ps1`, `.\scripts\run_v2_checks.ps1`, then `python scripts/stateless_sweep.py`, `.\scripts\run_pipeline.ps1 -Live` and `-LLMBaselines`. Tests: `python -m pytest -q` (33 tests).
