# MAPIS — Multi-Agent Prompt Injection Shield: Final Report

Team A1: Dodla Nithya Sai, Vishnu Vardhan, Sreekar Reddy, Beena Reddy. Supervisor: Prof. Sripriyan. Final review: 22 October 2026.

All numbers below were measured and come from `results/` (mirrored in Drive `mapis_results`).

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

### 4.1 Headline (session level, 2,304 held-out sessions, mean ± std over 5 training seeds: 42, 2, 3, 4, 5)

| System | Recall | FPR | Accuracy |
|---|---|---|---|
| **MAPIS** | **98.0 ± 0.6 %** | **0.9 ± 0.8 %** | **98.5 %** |
| Stateless DeBERTa (same data, event only) | 94.1 ± 0.9 % | 33.2 ± 3.5 % | 82.0 % |
| Llama Guard 3-1B | 86.1 % | 90.3 % | 52.3 % |
| ProtectAI deberta-v3 injection v2 | 53.3 % | 49.5 % | 52.1 % |
| Prompt Guard 2 (86M) | 7.5 % | 0.1 % | 48.4 % |

MAPIS per set (recall / FPR, 5 seeds):
- Multi-hop: 100 % / 3.0 ± 3.0 % at the default hold cut-off (0.50). At the default cut-off two of five seeds exceed 5 % (5.3 and 7.7 %). With a cut-off chosen on the validation split only (`scripts/calibrate_mapis.py`), every seed stays ≤ 1.8 % (1.2→0.6, 5.3→1.8, 0.0→0.0, 7.7→0.6, 0.6→0.0 %; mean 3.0→0.6 %) with recall unchanged.
- Adaptive: 100 % / 0.4 % (0.0 % in four seeds, 1.8 % in one), all six techniques.
- InjecAgent direct harm: 99.4 % / 0 %. ASB: 100 % / 0 %.
- Decomposed: 100 / 0. v1: 100 / 0.
- BIPIA (never trained on): 95.8 % / 1.4 % (stateless 94.5 % / 2.2 %).

### 4.2 Stateless detection at a matched false-positive budget

At the default threshold the stateless model buys 86.5 % multi-hop recall with a 51 % FPR (5 seeds), because it flags the user-authorized twins. Holding it to ≤ 5 % FPR (threshold chosen on validation, applied to test; 5-seed means):

| Set | Stateless recall | MAPIS recall |
|---|---|---|
| Multi-hop | 4.3 % | 100 % |
| Adaptive | 6.1 % | 100 % |
| InjecAgent-DH | 88.5 % | 99.4 % |
| ASB | 97.8 % | 100 % |

On multi-hop and adaptive attacks the gap is about 96 and 94 points, against the target of ≥ 20. The thresholds picked on validation did not hold exactly on test (seed 3 multi-hop FPR 7.7 %, seed 2 adaptive 8.8 %), so these stateless recalls are generous to the baseline. On RealHarm the explicit injection text makes message-level detection competitive, and the gap is ≤ 11 points.

### 4.3 The evasive attacker (MAPIS-Adaptive, 576 test sessions, seed 42, recall / FPR)

| Technique | MAPIS | Stateless |
|---|---|---|
| Obfuscated item ("x at host dot example", `hxxps://h[.]example`) | 100 / 0 | 83.3 / 37.5 |
| Split item (mailbox in one document, domain in another) | 100 / 0 | 83.3 / 45.8 |
| Hidden characters (zero-width, full-width @) | 100 / 0 | 87.5 / 43.8 |
| Paraphrased claim | 100 / 0 | 87.5 / 45.0 |
| Long delay (8 hops between plant and action) | 100 / 0 | 87.5 / 46.2 |
| Combination | 100 / 0 | 90.0 / 51.2 |

Before the upgrade the old model with the old matching caught 64.6 % at 2.9 % FPR; normalisation and fragment matching raised it to 100 % at 3.9 %; adversarial training brought the FPR to 0.0 %. Five seeds: 100 % / 0.4 %.

### 4.4 Public guardrails by set (recall / FPR; MAPIS and stateless 5-seed means)

| Set | MAPIS | Stateless | Llama Guard | ProtectAI | Prompt Guard 2 (recall) |
|---|---|---|---|---|---|
| All 2,304 | 98.0 / 0.9 | 94.1 / 33.2 | 86.1 / 90.3 | 53.3 / 49.5 | 7.5 (FPR 0.1) |
| MultiHop | 100 / 3.0 | 86.5 / 51.1 | 100 / 100 | 70.8 / 63.9 | 0 |
| Adaptive | 100 / 0.4 | 86.6 / 43.0 | 100 / 100 | 66.1 / 64.1 | 0 |
| BIPIA (held-out part) | 95.8 / 1.4 | 94.5 / 2.2 | 72.5 / 65.5 | 44.7 / 56.5 | 1.0 |

### 4.5 Ablation (seed 42, 2,304 sessions)

| System | Recall | FPR |
|---|---|---|
| Full MAPIS | 97.0 % | 0.2 % |
| Learned model only (no rule fusion) | 97.0 % | 0.1 % |
| Without the provenance rule | 97.0 % | 0.1 % |
| Same model without session memory | 94.7 % | 33.6 % |
| Regex rules only | 12.5 % | 0.0 % |

Removing the session memory raises the FPR from 0.2 % to 33.6 % (multi-hop twins: the stateless model flags 89 % of authorized and 77 % of designated twins; MAPIS 0.6 % and 0 %). The fusion rules change no decision once the classifier reads the session signals; they remain as a safety net and as the operator-facing explanation.

### 4.6 Cost

63.0 ms per event single and 51.4 ms batched on an RTX 3050 laptop GPU (`results/evaluate.json`), against the 200 ms target.

### 4.7 Targets

| Target | Result |
|---|---|
| Accuracy ≥ 90 % | 98.5 % (5 seeds) |
| FPR ≤ 5 % | 0.9 % overall; multi-hop 3.0 % mean at the default cut-off, ≤ 1.8 % in every seed with the validation-calibrated cut-off |
| < 200 ms per message | 63 ms |
| ≥ 20 points recall gain on multi-hop | +96 points at matched FPR (+13.5 at the default threshold) |

## 5. Limits

- MultiHop and Adaptive are template-generated (held-out families, phrasings and tools; real carrier text).
- Provenance follows items with a recognisable shape (emails, URLs, IBAN-like ids, long numbers); an attack that only changes a short plain value leaves no item to trace.
- Two seeds of five have a multi-hop FPR above 5 % at the default cut-off; the validation-calibrated cut-off fixes it in all five seeds.
- On single-hop BIPIA there is no cross-hop evidence, so stateless recall is within seed variance of MAPIS.
- The rule signals add nothing measurable once the classifier has the session signals.
- The demonstration testbed is scripted; the public guardrails run with their default thresholds.
- Related work already covers parts of this space (Prompt Infection, G-Safeguard, LlamaFirewall AlignmentCheck). MAPIS's contribution is the combination: a small classifier with stateful session signals at a framework-agnostic tap, fragment attacks with matched benign twins, a provenance trace and a tiered response.

## 6. Future work

- Action-argument checks: compare every action argument with the user's request (changed values, extra privilege flags, destinations relayed by another agent).
- Harder evaluation: a hand-written test set independent of the generators, and attacks aimed at the session record itself.
- Live LLM agents (AgentDojo) with MAPIS in the loop, and LLM-based guardrails (NeMo Guardrails, a history-aware LLM judge) as baselines.
- Multimodal content, more frameworks, production hardening.

## 7. Reproduction

`CLAUDE.md` §6 has the exact commands. In short: `.\scripts\run_pipeline.ps1 -Seeds 5`, `python scripts/stateless_sweep.py`, `python scripts/calibrate_mapis.py`. Tests: `python -m pytest -q`.
