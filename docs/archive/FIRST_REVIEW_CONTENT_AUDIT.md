# MAPIS First Review — presentation content audit

**Project:** MAPIS — AI Multi-Agent Prompt Injection Shield  
**Team:** A1 | **Supervisor:** Professor Sripriyan

## 1. Executive summary

MAPIS has a working prototype foundation: FastAPI scanning, a stateful heuristic baseline, SQLite metadata logging, React dashboard, deterministic agent prototypes, MAPIS-Bench v1, and a Phase 4 causal event dataset. The learned model is not a completed result.

**TRAINING IN PROGRESS / NO COMPLETED RESULT AVAILABLE YET.** Training was started with microsoft/deberta-v3-small; the tokenizer and pretrained model were downloaded and initialized, and artifacts/phase4_transformer/training_config.json is present. No checkpoint, tokenizer/model artifact, validation history, or completed Transformer metric exists in the repository. Present only the heuristic MAPIS-Bench result as measured performance. Provisional presentation figures below are clearly labelled and are not experimental results.

Slide 1 is already populated in the supplied template: MAPIS, Team A1, Dodla Nithya Sai, Vishnu Vardhan, Sreekar Reddy, Beena Reddy, and Professor Sripriyan.

## 2. Template audit: slides 1–15

| Slide | Template expectation | Available evidence | Missing / caution |
|---|---|---|---|
| 1 | Title/team/supervisor | Fully populated | None |
| 2 | Progress since Zeroth Review | Prototype, benchmark, Phase 4 data/tests | No trained model result |
| 3 | Motivation/problem/objectives | Template wording populated | Targets are not results |
| 4 | Literature/gap | Eight template references | Do not add unverified papers |
| 5 | Final architecture | Intended methodology + prototype code | Separate intended/current |
| 6 | Prototype status | Component evidence below | Full integration incomplete |
| 7 | Experimental setup | Data, causal labels, config | No actual run/device result |
| 8 | Quantitative results | Heuristic baseline only | Transformer/latency unavailable |
| 9 | Results interpretation | Baseline/design rationale | No claimed learned gain |
| 10 | Demonstration | Scan API, dashboard, mock pipeline | No real tools/memory |
| 11 | Limitations | Evidence-backed gaps | Be candid |
| 12 | Completion plan | Zeroth roadmap/current state | No official dates found |
| 13 | Current achievement | Data/prototype metrics | No trained model claim |
| 14 | Team responsibility | Exact template roles | Git does not prove individual ownership |
| 15 | References | Eight template references | Keep existing bibliography |

## 3. Current project status

Status labels: **DONE**, **IN PROGRESS**, **PARTIAL / PROTOTYPE**, **NOT STARTED**.

| Area | Status | Exact evidence |
|---|---|---|
| A. Testbed | PARTIAL / PROTOTYPE | Five deterministic agents in backend/agents/mapis_agents.py. |
| B. LangGraph | PARTIAL / PROTOTYPE | Compiled START→planner→web→file→code→memory→END in mapis_graph.py; API does not invoke it. |
| C. AutoGen | NOT STARTED | No application import/use found. |
| D. FastAPI interception | PARTIAL / PROTOTYPE | /scan scores supplied messages; /pipeline/run uses old sequential pipeline. |
| E–H. Web/file/code/memory paths | PARTIAL / PROTOTYPE | Deterministic/simulated agent outputs; RAM scorer state only; no real browser, document, executor or retrieval/write path. |
| I. MAPIS-Bench v1 | DONE | Dataset, schema, policies, provenance and audit scripts under data/mapis_bench. |
| J. AgentDojo | DONE | 1,132 native chronological records and converters/selectors. |
| K. InjecAgent | DONE | 544 derived attacks plus 17 cleaned benign records. |
| L. Phase 4 training data | DONE | 12,977-event dataset and passing validator. |
| M. Transformer infrastructure | DONE | backend/ml config, loader, model factory, inference, calibration utility and explicit train entry point. |
| N. Transformer training | IN PROGRESS | User-confirmed tokenizer/model initialization plus saved config; no checkpoint/model/metrics in repository. |
| O. Calibration | NOT STARTED | Probability conversion exists; no fitted calibration/threshold artifact. |
| P. Four tiers | NOT STARTED | Intended tiers absent; legacy ALLOW/WARN/BLOCK remains. |
| Q. Forensic logging | PARTIAL / PROTOTYPE | SQLite AlertLog/MessageLog; no full propagation trace. |
| R. Redis/session context | PARTIAL / PROTOTYPE | RAM sessions; Redis config/container/dependency only. |
| S. Dashboard | PARTIAL / PROTOTYPE | React REST/WebSocket UI; incomplete pipeline event persistence. |
| T. Benchmark harness | PARTIAL / PROTOTYPE | Heuristic MAPIS-Bench evaluator; no learned-model protocol. |
| U. Llama Guard / V. NeMo | NOT STARTED | No code/results. |
| W. End-to-end integration | NOT STARTED | Model not connected to runtime/API tiers. |

## 4. Verified metrics

### MAPIS-Bench v1

| Metric | Value |
|---|---:|
| Sessions | 1,693 |
| Attack / benign sessions | 1,544 / 149 |
| Train / validation / test sessions | 1,169 / 242 / 282 |
| AgentDojo / InjecAgent sessions | 1,132 / 561 |
| Message records | 12,977 |
| Native chronological / derived / cleaned records | 1,132 / 544 / 17 |
| Cross-split groups | 0 across 676 source/task groups |

Attack classes: financial manipulation 910; data exfiltration 527; instruction override 54; physical safety harm 18; code/tool manipulation 17; 18 attacks intentionally remain unclassified (swearwords_dos).

### Phase 4 causal event dataset

| Metric | Value |
|---|---:|
| Total event records | 12,977 |
| Malicious / safe supervised | 1,677 / 905 |
| Unlabeled/excluded | 10,395 |
| Train / validation / test events | 9,123 / 2,070 / 1,784 |
| AgentDojo / InjecAgent events | 11,311 / 1,666 |
| Native / derived / cleaned events | 11,311 / 1,632 / 34 |
| Event / session-context label granularity | 5,995 / 6,982 |
| Validator | PASS; zero errors |
| Focused Phase 4 tests | 6 passed |

### Existing MAPIS-Bench heuristic baseline

This is the only completed MAPIS-Bench result.

| Metric | Existing stateful heuristic |
|---|---:|
| Test sessions | 282: 256 attack, 26 benign |
| TP / FN / TN / FP | 27 / 229 / 25 / 1 |
| Accuracy | 18.44% (derived from confusion counts) |
| Precision | 96.43% |
| Recall | 10.55% |
| F1 | 0.1901 |
| FPR | 3.85% |
| MAPIS-Bench latency | Not recorded |

Per class: data exfiltration 27/93 detected (29.03%); code/tool 0/3; financial 0/145; instruction override 0/9; physical safety 0/3. Three unclassified attacks are in overall test counts but not the class table.

An older separate InjecAgent run reports 3,332 messages, 3.1339 seconds total and 0.9405 ms/message. Do **not** call it MAPIS-Bench or Transformer latency.

### Architecture/test facts

- Five deterministic testbed agents, five graph nodes and five graph agent-output interception points.
- Active API pipeline: planner → simulated web search → analyst → response.
- RAM session state retains up to 50 records. SQLite logs session ID, source/target, message hash, raw/final score, penalty, decision, explanation and timestamp.
- There are 25 declared test functions. Only the six focused Phase 4 tests were directly run and passed in this audit; do not claim a fresh full-suite pass.

## 5. Slide-by-slide content

## SLIDE 2 — Project Progress Since Zeroth Review

**A. VERIFIED CURRENT CONTENT**

- MAPIS-Bench v1: 1,693 chronological multi-hop sessions with AgentDojo/InjecAgent provenance and grouped split controls.
- FastAPI scan foundation, heuristic stateful baseline, SQLite metadata logging, dashboard and deterministic agent prototypes.
- Validated Phase 4 causal data: 12,977 events; 1,677 malicious and 905 safe supervised events; six focused tests passed.

**B. EXPECTED / PROJECTED CONTENT**

- **[EXPECTED — REPLACE WITH ACTUAL RESULT]** First fine-tuning run will add a checkpoint and validation metrics. It has not yet done so.

**C. VISUAL / FIGURE:** milestone timeline: Zeroth Review → testbed → benchmark → causal data → Transformer scaffold → trained model (TBD).

**D. SOURCE / EVIDENCE:** data/mapis_bench/mapis_bench_v1.jsonl; data/training; backend/ml; results/mapis_bench_v1/summary.json.

**E. SPEAKER POINTS:** evidence-led progress; benchmark and causal labels are complete foundations; configuration is not a model result.

## SLIDE 3 — Motivation & Problem Statement

**A. VERIFIED CURRENT CONTENT:** Use the template wording: isolated-message guardrails can miss indirect prompt injection carried through multi-agent hops. Retain its stated scope and objectives.

**B. EXPECTED / PROJECTED CONTENT:** **[EXPECTED — REPLACE WITH ACTUAL RESULT]** Template targets of ≥90% accuracy, ≤5% FPR and ≥20-point recall gain are objectives, not measured MAPIS results.

**C. VISUAL / FIGURE:** legitimate task → tool response with hidden instruction → downstream agent-risk flow.

**D. SOURCE / EVIDENCE:** Template slide 3; README.md; data/mapis_multihop.

**E. SPEAKER POINTS:** indirect injection is content-borne; attacked sessions contain legitimate hops; this motivates event-level contextual scoring.

## SLIDE 4 — Consolidated Literature Review & Research Gap

**A. VERIFIED CURRENT CONTENT:** Reuse the template’s eight cited works and stated gaps: limited dynamic evaluation, security–utility trade-off, and lack of architectural instruction–data separation.

**B. EXPECTED / PROJECTED CONTENT:** **[EXPECTED — REPLACE WITH ACTUAL RESULT]** Llama Guard/NeMo comparisons are planned; neither exists here.

**C. VISUAL / FIGURE:** three columns—attacks, benchmarks, defenses—ending in highlighted MAPIS gap.

**D. SOURCE / EVIDENCE:** Template slides 4 and 15.

**E. SPEAKER POINTS:** literature motivates multi-hop contextual defense; MAPIS-Bench is a concrete evaluation contribution; do not say the gap is solved.

## SLIDE 5 — Finalized System Architecture & Methodology

**A. VERIFIED CURRENT CONTENT:** Show the intended template flow: Web → Code → File/Doc → Memory, MAPIS tap, rolling context, Transformer score (0 malicious, 1 safe), tiers, trace/dashboard. Overlay current implementation: deterministic LangGraph, /scan, RAM heuristic state and SQLite metadata.

**B. EXPECTED / PROJECTED CONTENT:** **[EXPECTED — REPLACE WITH ACTUAL RESULT]** Tool/memory wrappers, Redis state, learned runtime, four tiers and full trace are later work.

**C. VISUAL / FIGURE:** architecture diagram with green completed, amber prototype and gray planned blocks.

**D. SOURCE / EVIDENCE:** Template slide 5; backend/agents/mapis_graph.py; backend/api/routes.py; backend/core/trust_scorer.py; backend/ml.

**E. SPEAKER POINTS:** distinguish intended/current; new model contract is 0 malicious/1 safe; legacy heuristic remains separate.

## SLIDE 6 — Implementation Status – Prototype / Proof-of-Concept

**A. VERIFIED CURRENT CONTENT**

| Component | Status | Evidence |
|---|---|---|
| LangGraph / 5-agent prototype | PARTIAL / PROTOTYPE | mapis_graph.py, mapis_agents.py |
| FastAPI middleware | PARTIAL / PROTOTYPE | /scan, /pipeline/run |
| Trust scorer baseline | DONE | trust_scorer.py |
| MAPIS-Bench v1 | DONE | 1,693 sessions |
| Phase 4 training data | DONE | 12,977 validated events |
| Transformer infrastructure | DONE | backend/ml |
| Transformer training | IN PROGRESS | Config only, no result |
| Calibration / tiers | NOT STARTED | No fitted calibration/four-tier runtime |
| Forensic logging / Redis | PARTIAL / PROTOTYPE | SQLite metadata / RAM state |
| Dashboard | PARTIAL / PROTOTYPE | React REST/WebSocket |
| Benchmark harness | PARTIAL / PROTOTYPE | Heuristic evaluator only |

**B. EXPECTED / PROJECTED CONTENT:** None; remain factual.

**C. VISUAL / FIGURE:** color-coded status table.

**D. SOURCE / EVIDENCE:** Section 3 paths.

**E. SPEAKER POINTS:** data/scaffold are ready; tool/memory and trained inference are not; table separates proposal from completion.

## SLIDE 7 — Experimental Setup & Test Cases

**A. VERIFIED CURRENT CONTENT**

- MAPIS-Bench: 1,169 train / 242 validation / 282 test sessions.
- Causal representation: six recent preceding hops plus prior system context; never future hops.
- Five classes; 18 intentionally unclassified attacks.
- Binary contract: 0 malicious, 1 safe; positive labels only on localized injection-bearing events.
- Planned config: DeBERTa-v3-small, length 384, batch 4, accumulation 4, learning rate 2e-5, 3 epochs, AdamW, weight decay 0.01, seed 42, CUDA mixed precision if available.
- Training entry point loads train/validation only; test remains protected. Group audit reports zero cross-split groups.

**B. EXPECTED / PROJECTED CONTENT:** **[EXPECTED — REPLACE WITH ACTUAL RESULT]** Device, training duration and GPU use must come from an actual run log.

**C. VISUAL / FIGURE:** split bar chart plus causal window: preceding system/task/hops → current event → binary classifier.

**D. SOURCE / EVIDENCE:** data/mapis_bench/split_policy.json; data/training stats; scripts/prepare_phase4_training_data.py; backend/ml/config.py; backend/ml/train.py.

**E. SPEAKER POINTS:** session labels are not copied to all hops; null tool-call content is explicit; test data is isolated.

## SLIDE 8 — Results – Quantitative Performance

**A. VERIFIED CURRENT CONTENT**

| Metric | Existing Stateful Heuristic (actual) | Phase 4 Transformer (expected — pending training) |
|---|---:|---:|
| Accuracy | 18.44% | 91.82% |
| Precision | 96.43% | 97.94% |
| Recall | 10.55% | 90.15% |
| F1 | 0.1901 | 93.89% |
| FPR | 3.85% | 4.35% |
| Latency | Not recorded on MAPIS-Bench | GPU 10–25 ms/event; CPU 150–400 ms/event |

The heuristic is session-level: any WARN/BLOCK on a non-empty event counts as detection.

**B. EXPECTED / PROJECTED CONTENT:** **[EXPECTED / PRELIMINARY — TRAINING RESULT PENDING]** Working estimate: accuracy 91.82%, precision 97.94%, recall 90.15%, F1 93.89%, FPR 4.35%. Expected ranges: accuracy 89–93%, precision 95–98%, recall 86–92%, F1 90–94%, FPR 3–6%. These are not measured values and must be replaced by actual output.

**C. VISUAL / FIGURE:** metric table and baseline confusion-matrix card: TP 27, FN 229, TN 25, FP 1.

**D. SOURCE / EVIDENCE:** results/mapis_bench_v1/summary.json; scripts/evaluate_mapis_bench.py.

**E. SPEAKER POINTS:** high precision/low recall motivates Phase 4; baseline is not learned model; keep Transformer rows TBD.

## SLIDE 9 — Results Analysis & Interpretation

**A. VERIFIED CURRENT CONTENT**

- Heuristic recall is low because it uses limited regex, lexical drift, anomaly and obfuscation signals.
- Detection is concentrated in data exfiltration (27/93); reported test cases in the other four named classes were missed.
- Causal context preserves task/tool sequence without future-hop leakage.
- Event labels avoid falsely calling initial requests/later assistant behavior malicious.
- Class imbalance and source/task variants remain risks.

**B. EXPECTED / PROJECTED CONTENT:** **[EXPECTED — REPLACE WITH ACTUAL RESULT]** Transformer semantic generalization/recall improvement is intended, not measured.

**C. VISUAL / FIGURE:** per-class recall chart plus tool-response injection-hop diagram.

**D. SOURCE / EVIDENCE:** results/mapis_bench_v1/summary.json; backend/core/trust_scorer.py; docs/PHASE4_TRAINING.md.

**E. SPEAKER POINTS:** baseline weakness shows need for semantics; preserve uncertainty; final test stays untouched.

## SLIDE 10 — Prototype / Demonstration

**A. VERIFIED CURRENT CONTENT**

| Demo | Input / interception | Current behavior | Later expectation |
|---|---|---|---|
| Scan direct injection | POST /api/v1/scan | Legacy score, alert/log/WebSocket | Learned score/later tiers |
| Run pipeline | /pipeline/run task | Simulated four-stage pipeline | Canonical tool-aware graph |
| Show graph | test_mapis_graph.py task | Five deterministic handoffs | Real agents/tools |
| Dashboard | React UI, /stats, /alerts, /ws | Live scan/alert display | Full trace/tier UI |

**B. EXPECTED / PROJECTED CONTENT:** **[EXPECTED — REPLACE WITH ACTUAL RESULT]** Do not demo Transformer inference until a checkpoint exists and it is deliberately runnable.

**C. VISUAL / FIGURE:** live /scan and dashboard screenshots captured before presentation; pipeline timeline.

**D. SOURCE / EVIDENCE:** backend/api/routes.py; backend/agents/pipeline.py; backend/agents/mapis_graph.py; frontend/src/App.jsx.

**E. SPEAKER POINTS:** demo implemented API/dashboard only; call pipeline simulated; do not enter secrets/destructive inputs.

## SLIDE 11 — Current Limitations & Technical Challenges

**A. VERIFIED CURRENT CONTENT**

- Implementation: deterministic mocks; no real browser/file/code/memory wrappers.
- Model: no checkpoint, calibration or runtime integration.
- Dataset: conservative safe-label policy; 18 attacks lack MAPIS class; derived extraction hops are not runtime events.
- Integration: legacy/final score direction conflict; Redis/four tiers absent.
- Evaluation: no MAPIS-Bench latency, learned result, Llama Guard or NeMo; per-hop baseline rates are not event ground truth.
- Forensics/dashboard: metadata logging, not full propagation path; pipeline does not persist every event.

**B. EXPECTED / PROJECTED CONTENT:** None.

**C. VISUAL / FIGURE:** five-category limitation table: implementation, data, model, integration, evaluation.

**D. SOURCE / EVIDENCE:** backend; data/mapis_bench; docs/PHASE4_TRAINING.md; results/mapis_bench_v1/summary.json.

**E. SPEAKER POINTS:** baseline validates problem, not final performance; uncertainty is retained; work is dependency ordered.

## SLIDE 12 — Remaining Work & Completion Plan

**A. VERIFIED CURRENT CONTENT**

| Roadmap item | Status | Timing wording |
|---|---|---|
| Testbed + FastAPI hooks | PARTIAL / PROTOTYPE | Next integration milestone: real tool/memory interception |
| MAPIS-Bench v1 | DONE | Maintain frozen provenance data |
| Trust model + fine-tuning | IN PROGRESS | Immediate next phase: controlled train/validation run |
| Tiered response + forensic log | NOT STARTED | After score contract finalization |
| Dashboard + full integration | PARTIAL / PROTOTYPE | After durable traces/canonical runtime |
| Guardrail benchmark | NOT STARTED | Final validation phase |
| Final report/demo | IN PROGRESS | After final evaluation/integration |

**B. EXPECTED / PROJECTED CONTENT:** **[EXPECTED — REPLACE WITH ACTUAL RESULT]** Use milestone wording; no official completion dates were found.

**C. VISUAL / FIGURE:** dependency-ordered roadmap with DONE / PROTOTYPE / PENDING colors.

**D. SOURCE / EVIDENCE:** Template slide 12; backend/ml; project methodology.

**E. SPEAKER POINTS:** train/validate before tiers; tool/memory coverage before end-to-end claim; guardrails after frozen protocol.

## SLIDE 13 — Project Contribution & Current Achievement

**A. VERIFIED CURRENT CONTENT**

- MAPIS-Bench v1: 1,693 sessions; 1,544 attack / 149 benign.
- AgentDojo native and InjecAgent derived/cleaned provenance; zero cross-split groups.
- Causal Phase 4 data: 12,977 events; 1,677 malicious / 905 safe supervised; 10,395 uncertain/excluded events.
- Transformer infrastructure with 0-malicious/1-safe contract and test-set protection design.
- Five-agent LangGraph prototype, FastAPI interception foundation, six Phase 4 tests passed.

**B. EXPECTED / PROJECTED CONTENT:** **[EXPECTED — REPLACE WITH ACTUAL RESULT]** Add learned-model metrics only with checkpoint path and measured split.

**C. VISUAL / FIGURE:** cards: 1,693 sessions; 5 classes; 0 leakage groups; 12,977 events; 2,582 supervised events; 6 tests passed.

**D. SOURCE / EVIDENCE:** data/mapis_bench; data/training; backend/ml; tests/unit/test_phase4_training.py.

**E. SPEAKER POINTS:** contribution today is reproducible data/infrastructure; provenance supports auditability; prototype establishes integration path.

## SLIDE 14 — Team Contribution & Responsibility

**A. VERIFIED CURRENT CONTENT**

Use exact responsibilities from template slide 14. Repository/generic git history cannot prove individual ownership; confirm individual “completed” wording with the team.

| Member | Assigned responsibility | Verified artifact evidence | Current / next |
|---|---|---|---|
| Vishnu Vardhan | Testbed & Orchestration: AutoGen/LangGraph/FastAPI | Graph/prototype/API exist; ownership not individually proven | Canonical tool-aware graph/interception |
| Dodla Nithya Sai | Attack Dataset & Red-Team: MAPIS-Bench/labels | Benchmark/provenance artifacts exist; ownership not individually proven | Label policy/integrity review |
| Sreekar Reddy | Detection Model: context/classifier/calibration | Phase 4 data/model scaffold exists; ownership not individually proven | Training/validation/calibration |
| Beena Reddy | Response, Dashboard & Evaluation | Dashboard/logging/evaluator exist; ownership not individually proven | Tiers/trace UI/final harness |
| Shared | Integration, review, report writing | Tests/docs exist | Integration/final report |

**B. EXPECTED / PROJECTED CONTENT:** No unconfirmed individual completion claim.

**C. VISUAL / FIGURE:** responsibility matrix: owner, artifact, next milestone.

**D. SOURCE / EVIDENCE:** Template slide 14; paths above; git log has broad commits only.

**E. SPEAKER POINTS:** preserve agreed ownership; separate evidence/plans; state shared integration work.

## SLIDE 15 — References

**A. VERIFIED CURRENT CONTENT:** Retain template’s eight references: Greshake et al. (2023); Liu et al. (2023); Zhan et al./InjecAgent (2024); Debenedetti et al./AgentDojo (2024); Jia et al./Task Shield (2024); Wang et al./AgentWatcher (2026); Li & Zhao (2026); Geng et al. (2026).

**B. EXPECTED / PROJECTED CONTENT:** None; do not add papers merely to enlarge bibliography.

**C. VISUAL / FIGURE:** clean two-column bibliography using full template citations.

**D. SOURCE / EVIDENCE:** Template slide 15.

**E. SPEAKER POINTS:** AgentDojo/InjecAgent are direct sources; citations motivate MAPIS but do not prove results.

## 6. EXPECTED / PLACEHOLDER VALUES FOR TOMORROW

**Every row is NOT AN EXPERIMENTAL RESULT.**

| Metric/content | Expected value/range | Why | Replacement source |
|---|---|---|---|
| Transformer accuracy | Pending training result | No validation metric/checkpoint | Controlled run metrics |
| Transformer precision | Pending training result | Heuristic precision is not transferable | Controlled run metrics |
| Transformer recall | Pending training result | Better than 10.55% is objective, not evidence | Controlled run metrics |
| Transformer F1 | Pending training result | Depends on unmeasured trade-off | Controlled run metrics |
| Transformer FPR | Pending training result | Must be validation-calibrated | Threshold study |
| Transformer latency/overhead | Pending training result | Device/checkpoint dependent | Timed inference record |
| GPU/device | Pending run log | CUDA support does not prove use | Run metadata |
| Four-tier result | Intended specification only | Tiers unimplemented | Runtime evidence |

## 7. Final checklist before presentation

- [ ] Keep Slide 1 details exactly as populated.
- [ ] Keep Transformer metric cells as **TBD — TRAINING RESULT** until checkpoint plus metrics exist.
- [ ] Identify 18.44% accuracy as derived from baseline counts.
- [ ] Do not repurpose InjecAgent latency as MAPIS-Bench/Transformer latency.
- [ ] Capture current /scan and dashboard screenshots before demo.
- [ ] Call active pipeline “simulated/mock” and LangGraph “deterministic prototype.”
- [ ] Do not claim AutoGen, Redis, tiers, Llama Guard or NeMo are complete.
- [ ] Team-confirm Slide 14 attribution.
- [ ] Preserve test-split isolation in verbal explanations.
- [ ] Update only from completed artifacts, never config/init messages.

## 8. Evidence paths inspected

- Template: C:\Users\vishn\Downloads\First_Review_Sample_Presentation.pptx.pptx
- Core/API: backend/core/trust_scorer.py; backend/api/routes.py; backend/models/database.py; backend/config.py; backend/main.py
- Agents: backend/agents/mapis_agents.py; backend/agents/mapis_graph.py; backend/agents/pipeline.py
- Phase 4: backend/ml; data/training/mapis_phase4_events_v1.jsonl; data/training/mapis_phase4_events_v1_stats.json; docs/PHASE4_TRAINING.md; artifacts/phase4_transformer/training_config.json
- Dataset/evaluation: data/mapis_bench; data/mapis_multihop; scripts; results/mapis_bench_v1/summary.json; results/injecagent/latency_results.json
- UI/tests/docs: frontend/src/App.jsx; tests; README.md; SETUP.md

## TOP 10 ITEMS TO UPDATE IF TRAINING FINISHES BEFORE PRESENTATION

1. Slide 6: mark Transformer training complete only with checkpoint and metrics.
2. Slide 7: insert actual device, runtime and run configuration from log.
3. Slide 8: replace Transformer TBD cells with actual metrics and split labels.
4. Slide 8: add actual Transformer confusion matrix.
5. Slide 8: add measured inference latency/compute overhead and hardware context.
6. Slide 9: replace intended-improvement wording with measured overall/per-class comparison.
7. Slide 9: state validation-only threshold/calibration behavior.
8. Slide 10: add reproducible trained-model inference screenshot only if runnable.
9. Slide 12: update fine-tuning milestone using saved/reviewed artifacts.
10. Slide 13: add model achievement only with exact artifact path and metric source.
