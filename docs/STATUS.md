# MAPIS status (verified in this repository)

## Implemented and tested (pytest, no GPU needed)
- Four-tier response PASS / FLAG / QUARANTINE / BLOCK on the 0=malicious scale, channel suspension, quarantine review API.
- Session store: Redis with in-memory fallback; bounded window; goal vector text never overwritten by agent output.
- Four stateful signals + noisy-OR fusion + session sensitivity; forensic propagation trace (origin → relay → action).
- 5-agent LangGraph testbed over a simulated environment (web / files / memory / email); tap on every hop incl. memory writes/reads and tool calls.
- FastAPI tap, SQLite forensic log, WebSocket push, React dashboard (timeline, alerts, traces, quarantine review).
- Training / calibration (temperature) / evaluation code; train/serve text parity is unit-tested.

## NOT yet measured (needs the laptop)
- Any DeBERTa result. No completed training exists (only an abandoned epoch-1 checkpoint on an old CPU laptop). The First Review slide figures
  (89.97 % acc, 87.5 % recall, 4.35 % FPR, TP 231 / FN 33 / FP 5 / TN 110) are provisional placeholders and must be removed from the deck.
- The only real quantitative result is the old heuristic baseline on MAPIS-Bench v1 test (282 sessions): recall 10.55 %, precision 96.43 %, FPR 3.85 %.
- Latency of the full shield with the transformer; thresholds tuned on validation.
- Llama Guard / NeMo baselines (adapters written, never run).

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

## Known limits to state openly
- MAPIS-Bench v1 labels the injection-bearing *tool event*; most attacks there are single-injection, so v1 alone cannot show a
  stateful advantage. `scripts/generate_decomposed.py` builds template-seeded decomposed attacks (split by template family) for that.
  It is synthetic and was written around the provenance mechanism, so results on it demonstrate the mechanism, not real-world recall.
- Phase-4 v1 labels were shortcut-prone (measured on the real data: a role-only rule scored 89.4 % accuracy / 100 % recall / 34.8 % FPR; every AgentDojo attack carries a literal
  `<INFORMATION>` tag; InjecAgent had no benign tool responses). v2 fixes this: tags stripped everywhere, 717 clean pre-injection AgentDojo tool outputs and 544 InjecAgent
  minimal-pair "clean twins" as hard negatives (synthetic neutral filler, disjoint per split), and a template-held-out `test_ood` split. Role-only now scores 0 % recall.
- Even so, on v2 a TF-IDF + logistic regression scores ~98 % (test) and ~100 % (test_ood): injected instructions are blatantly imperative in these benchmarks. Single-event
  accuracy cannot demonstrate an advantage; the decomposed multi-hop benchmark is where the stateful claim has to be shown.
- Provenance can false-positive when a legitimate destination comes from a tool result (e.g. "pay the bill in the file").
  Sources the user explicitly named in the task (e.g. the file in 'pay the bill in bill.txt') are trusted origins; anything else lands in QUARANTINE
  for a human. The remaining false-positive cost is measured on the benign sessions in the benchmark.
- Fusion weights are defaults; tune on validation before the final review.
- AutoGen is not implemented (LangGraph only).
