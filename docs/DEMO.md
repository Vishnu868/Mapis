# MAPIS live demo (operator console)

## Who the dashboard is for
MAPIS sits between the agents of a multi-agent LLM system. The **end user never sees MAPIS**: they give a task, and if an
agent is about to act on injected content (send data to an attacker, pay a planted account, unlock a door) the action is
simply not delivered. The dashboard is the **operator / security-admin console** of the team that runs the agent system:

| Tab | What the operator does with it |
|---|---|
| **Live monitor** | Watches every message the agents exchange, scored live (PASS / FLAG / QUARANTINE / BLOCK), the trust timeline of the session, and the alerts. Each alert has the **forensic trace** origin -> relay -> action (which untrusted document planted the item, which agent relayed it, which action used it). **QUARANTINE** messages are held: the operator clicks *Release* (deliver) or *Reject* (drop) - the human-in-the-loop step from the abstract. A BLOCK also suspends the agent channel. The testbed runs on **LangGraph or AutoGen** with a clean task, an overt injection or a decomposed (no-cue) attack. |
| **Session inspector** | Replays any held-out benchmark session (multi-hop, RealHarm, BIPIA, ...) through the live shield, hop by hop: tier, trust, the action arguments, the reasons and the session signals (authority claims, untrusted-item reuse, user-supplied items, unrequested action, drift). Used to explain *why* MAPIS held one session and passed its benign twin. |
| **Results** | The measured benchmark tables and charts (MAPIS vs stateless DeBERTa vs Llama Guard / NeMo; overall, multi-hop, RealHarm, BIPIA; 3-seed mean +/- std), read from `results/*.json`. |

## Run it (on the GPU laptop, with the trained model)
```powershell
cd E:\mapis\mapis\Mapis
# terminal 1 - API (uses artifacts\mapis_detector; Redis optional, falls back to in-memory)
python -m uvicorn backend.main:app --port 8000
# terminal 2 - dashboard
cd E:\mapis\mapis\Mapis\frontend
npm install        # first time only
npm start          # opens http://localhost:3000
```
Optional real Redis: `docker run -p 6379:6379 redis:7` before starting the API (otherwise the header shows "session store: memory").

## Demo script (5 minutes)
1. Live monitor -> LangGraph -> *Clean task* -> Run: every hop PASS, the email is sent.
2. *Decomposed attack* -> Run: no message contains an instruction; the email to the planted address is QUARANTINED at the final hop,
   the trace shows file (origin) -> memory write -> memory read -> email action. Click *Reject*.
3. Same with **AutoGen** (framework selector): same verdicts through AutoGen's message hook.
4. Session inspector -> MAPIS-MultiHop -> an ATTACK -> Replay (held at the final action); then an *authorized* twin -> Replay (passes).
5. Results tab -> multi-hop table: MAPIS vs stateless vs Llama Guard.

`docs/screenshots/` shows the console running in the cloud sandbox with the rules-only fallback detector (no GPU there);
retake them on the laptop with the trained model for the report.
