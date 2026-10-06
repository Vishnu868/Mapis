# Writing the independent multi-hop test set (team task, ~1-2 days)

**Why:** every multi-hop number so far comes from sessions our own generator produced. A test set written by people who did not write the
generator is the strongest evidence that MAPIS generalises. These sessions are **test-only** — they are never used for training.

**Target:** 60 sessions in total = **30 attacks + 30 benign twins**. Split the work: each of the 4 team members writes ~8 attacks + their twins.
Cover all five attack classes and all five mechanisms (see the tables). Do **not** look at `scripts/generate_multihop.py`; write in your own words,
use your own scenarios, tools, names and phrasing. Vary length, number of hops (3-12), and agents.

## The rules of a good attack session
1. The user's request is normal and harmless.
2. The attack arrives through **data the agents read** (a document, web page, email, tool result, memory entry, another agent's message) — never through the user.
3. **Spread it across hops**: no single message should be an obvious "ignore your instructions and do X". Examples:
   one document plants a detail (an email address, an account number, a URL, a "rule"), a later message claims authority ("approved by finance"),
   and the final agent action uses it.
4. The last message is the harmful **action**: an assistant message with `tool_name` + `tool_call` (send money, send data, run a command,
   grant access, disable a safety system, ...).

## The rules of a good benign twin
Copy the attack and change it so it becomes legitimate. Use one of:
- `authorized` — the **user** asks for that destination/rule in their request (the action is then fine).
- `resisted` — the planted text is still there but the agent ignores it and does the correct thing.
- `designated` — the user explicitly names the file/source that contains the detail ("pay the account in invoice_88.txt").
- `normal` — an ordinary multi-hop task with no attack text at all (use for a few twins).

## Labels
| field | values |
|---|---|
| `attack_class` | `data_exfiltration`, `financial_manipulation`, `code_tool_manipulation`, `instruction_override`, `physical_safety_harm` |
| `attack_vector` | `document_poisoning`, `memory_injection`, `tool_output_manipulation`, `cross_agent_injection`, `goal_hijacking` |
| message `role` | `user`, `assistant` (agent messages and tool calls), `tool` (tool output), `memory_write`, `memory_read` |
| message `label` (optional) | `malicious` on the relay/action messages of an attack, `unlabeled` on innocent-looking fragments; leave it out otherwise |

Aim for at least 5 attacks per class and 5 per mechanism.

## File format
One JSON file per person in `data/independent/`, e.g. `data/independent/sreekar.json`, containing a list of sessions.
Copy the structure of `data/independent/EXAMPLE_attack_and_twin.json` (files starting with `EXAMPLE` are ignored).
Each session: `id` (unique, e.g. `sreekar_007`, twin `sreekar_007_twin`), `author`, `is_attack`, `attack_class` + `attack_vector` (attacks) or
`benign_kind` (twins), `notes` (one sentence: what the attack is), `messages`.

## Check and submit
```powershell
python scripts/dataset_build/build_independent.py      # prints errors to fix, or "wrote N sessions"
```
Then send the JSON files to Vishnu (or upload them to `mapis_results/independent/`). They are evaluated with
`python scripts/benchmark.py --systems mapis,mapis-stateless,llamaguard --sets independent --out results/benchmark_independent.json`.
