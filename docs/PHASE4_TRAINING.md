# MAPIS Phase 4: training representation and model scaffold

`scripts/prepare_phase4_training_data.py` derives an event dataset from, but
never edits, `data/mapis_bench/mapis_bench_v1.jsonl`.  Every source hop becomes
an auditable record.  Its context contains only preceding hops (up to six most
recent plus preceding system messages); the current scoring event is separate.
No future hop appears in either context or model text.

The representation preserves source IDs, provenance, conversion type, role,
source/target, content state, tool calls, tool response fields, current hop,
and context hops.  An assistant hop with null content and a tool call is marked
`null_assistant_tool_call`; it is not silently treated as ordinary prose.

## Supervision policy

The session attack label is never copied to all of its messages. Positive
examples are only native AgentDojo `tool` events containing `<INFORMATION>` and
derived InjecAgent `tool_response` events, which the source conversion documents
as injection-bearing. Derived InjecAgent attacker-instruction extraction hops
are retained but unlabeled because they are not separate runtime events.

Safe examples are a conservative policy choice: non-empty text events from
native benign AgentDojo trajectories, and the user-request event from each
benign InjecAgent case. The benign InjecAgent tool-response template containing
the literal `<Attacker Instruction>` placeholder is explicitly unlabeled, so it
cannot teach the model that an attack marker is safe. Other attack-session hops,
empty events, and null-content assistant tool calls are retained as `unlabeled`
for forensic review but excluded from supervised loading.

Run:

```text
python scripts/prepare_phase4_training_data.py
python scripts/validate_phase4_training_data.py
```

## Model contract

`backend/ml/` is isolated from the legacy heuristic scorer. The default future
model is `microsoft/deberta-v3-small`, a binary sequence classifier where class
0 is `MALICIOUS` and class 1 is `SAFE`. Its trust score is `P(SAFE)`: **0 means
malicious and 1 means safe**. This is intentionally the reverse of the legacy
heuristic's score direction.

`TrainingConfig` defaults to max length 384, batch size 4, gradient
accumulation 4, three epochs, mixed precision on CUDA, and seed 42. This is a
conservative starting point for an RTX 3050-class GPU. LoRA is not added by
default because it has not yet been shown necessary; it should be introduced
only if a measured memory limit requires it.

The training command requires an explicit `--run`, uses train and validation
only, saves configuration/checkpoints/validation history, and never loads the
test split. No model has been trained or calibrated by this scaffold. Runtime
integration, tier thresholds, final evaluation, and guardrail comparison are
later phases.
