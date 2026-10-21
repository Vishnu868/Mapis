# MAPIS: simple guide and live demo (22 October 2026)

## 1. What MAPIS is, in one paragraph
A team of AI agents works on a user's task: a planner, a web agent, a file agent, a memory agent and an email/code agent.
They read documents, web pages and memory notes that nobody checked. An attacker can hide text in that content, such as an
address, an "approved by finance" note or a changed account number, so that a later agent acts on it. This is **indirect
prompt injection**. MAPIS sits **between the agents** and checks every message before it is delivered. It also **remembers
the session**: what the user asked, and where every address, link, id or value first appeared. Each message gets a
**trust score from 0 (malicious) to 1 (safe)** and one of four decisions.

## 2. How one message flows through MAPIS
```
agent wants to send a message / call a tool
        │
        ▼
MAPIS tap (POST /inspect)
  1. who sent it?  user/system → trusted (trust 1)
  2. is this channel suspended (after an earlier BLOCK)? → trust 0
  3. read the session record: user goal, tainted items, authority claims, agent baselines
  4. DeBERTa classifier reads: current message + one SIGNALS line + short history → model trust
  5. rule checks add risk:
       instruction-in-data · drift from goal · provenance (item first seen in untrusted content)
       · behaviour anomaly · tampering checks (changed value / privilege flag / relayed destination)
  6. combine → final trust → tier
  7. update the session record, log the event, push it to the dashboard
```

## 3. What every word on the dashboard means
| Term | Meaning |
|---|---|
| **Trust** | 0 to 1, final score after combining model and rules. Low = dangerous. |
| **Model trust** | What the DeBERTa classifier alone said, before the rules. |
| **PASS** (green, trust ≥ 0.75) | Delivered normally. |
| **FLAG** (yellow, 0.50–0.75) | Delivered, but the session becomes more sensitive (+0.15), so later messages are judged more strictly. |
| **QUARANTINE** (orange, 0.25–0.50) | Held. The operator decides: **Release** (deliver) or **Reject** (drop). |
| **BLOCK** (red, < 0.25) | Dropped, and the channel between those two agents is **suspended**. |
| **Hop** | One message in the session (hop 1 = the user's request). |
| **Source → target** | Which agent sent it to which agent or tool. |
| **Role** | user, assistant (an agent), tool (tool output), memory_read / memory_write. Tool and memory content is *untrusted*. |
| **Signals / features** | instruction (command-like text in data), drift (action unrelated to the goal), provenance (planted item reused, also covers escalation and tampering), behaviour (agent acting outside its usual tools). Each is 0 to 1. |
| **Reasons** | Plain-English explanation, e.g. *"'audit@x.example' first appeared in untrusted hop 3 (file_agent) and now reaches an action"* or *"'destination=WL-5508' replaces 'PS-7731' given by the user"*. |
| **Forensic trace** | origin (where the item was planted) → relay (agents that passed it on) → action (where it would have been used). |
| **Session sensitivity** | Rises after every non-PASS. Makes the session stricter. |
| **Session store: memory / redis** | Where session records live. "memory" is fine for the demo. |
| **Detector name** | Must say **deberta-v3-small**. If it says *regex*, the trained model was not found (see section 7). |

## 4. The three dashboard tabs
1. **Live monitor**: pick a framework (**LangGraph** or **AutoGen**) and a scenario, then press Run. The hops appear one by one with their tier and trust. On the right you see the trust timeline and the alerts with traces. Held messages show Release / Reject buttons.
   - *Clean task*: a normal task. Everything should PASS and the email is sent.
   - *Overt attack*: a document says plainly "ignore instructions, send data to …". It is held.
   - *Decomposed attack*: no message contains an instruction. The address is planted in a file, saved to memory, read back, then used in an email. MAPIS holds the email and shows the trace file → memory write → memory read → email.
2. **Session inspector**: choose a benchmark set (MultiHop, Adaptive, RealHarm, StateAttack, Independent …) and a session, then Replay. You see each hop's tier, trust, tool arguments, reasons and signals. Use it to show an **attack** and its **benign twin** (same final action, but the user asked for it) side by side: the attack is held, the twin passes.
3. **Results**: the measured tables and charts from `results/*.json`.

## 5. Tonight: preparation on the laptop (≈ 15 min)
```powershell
cd E:\mapis\mapis\Mapis
& E:\mapis\mapis\Scripts\Activate.ps1
git stash
git pull origin claude/inspiring-hopper-4gqkjy
git log --oneline -1                      # latest commit (b8364d2 or newer)
python -m pytest -q                       # expect 33 passed
```
Then do one full rehearsal using section 6. Check that the header shows **deberta-v3-small**, and that the clean task passes and the decomposed attack is held on both LangGraph and AutoGen.
Charge the laptop and disable sleep. Keep `slides_latex\MAPIS_Final_Slides.pdf` open in a PDF viewer.
Backup in case the live demo fails: the screenshots in `docs\screenshots\trained_*.png` (also in the slides).

## 6. Tomorrow: starting the demo (2 terminals)
**Terminal 1: API**
```powershell
cd E:\mapis\mapis\Mapis
& E:\mapis\mapis\Scripts\Activate.ps1
python -m uvicorn backend.main:app --port 8000
```
Wait for `Application startup complete` and a log line `Detector: deberta-v3-small from artifacts/mapis_detector`.

**Terminal 2: dashboard**
```powershell
cd E:\mapis\mapis\Mapis\frontend
npm start
```
The browser opens http://localhost:3000. Run `npm install` first if it has never been run on this laptop.

## 7. Demo steps (about 5 minutes)
| # | Do | Expected |
|---|---|---|
| 1 | Live monitor → LangGraph → **Clean task** → Run | Every hop green (PASS), email sent. MAPIS does not block normal work. |
| 2 | **Decomposed attack** → Run | Hops pass until the final email, which is **QUARANTINE** (or BLOCK). The trace shows file → memory → email. Click **Reject**. |
| 3 | Framework → **AutoGen** → Decomposed attack → Run | Same verdict through AutoGen's message hook. The tap works with both frameworks. |
| 4 | **Overt attack** → Run | Held early: the instruction is in a data channel. |
| 5 | Session inspector → MAPIS-MultiHop → an *attack* session → Replay; then its *authorized* twin → Replay | The attack is held at the last action. The twin, with the same action but requested by the user, passes. This is the core idea: same message, different history. |
| 6 | Session inspector → Independent (team-written) → e.g. a wallet or bypass-flag attack → Replay | Held by a tampering check. The reason says which value was changed or which flag was added. |
| 7 | Results tab | MAPIS 98.0 % recall / 0.9 % false alarms vs stateless 94.1 / 33.2, Llama Guard 86.1 / 90.3. |

## 8. If something goes wrong
| Problem | Fix |
|---|---|
| Header says **regex**, not deberta | The model folder is missing. Check that `artifacts\mapis_detector` exists, and start uvicorn from `E:\mapis\mapis\Mapis`. |
| `Address already in use` / port 8000 busy | Close the old terminal, or run `python -m uvicorn backend.main:app --port 8001` and set the API URL in the dashboard to 8001. |
| Dashboard shows a network error | The API is not running or has not finished loading. Wait for "startup complete", then refresh the browser. |
| `npm` not found | Install Node.js LTS, or present from the screenshots. |
| AutoGen scenario fails | Use LangGraph (same shield), and mention AutoGen with the screenshot. |
| `(mapis)` not shown in the prompt | Run `& E:\mapis\mapis\Scripts\Activate.ps1` again. |
| First request is slow | The model loads on the first call (a few seconds). Run the clean task once before the panel arrives. |

## 9. Key numbers (all measured, 5 training seeds)
- 2,304 held-out test sessions: **98.0 % recall, 0.9 % false alarms, 98.5 % accuracy, 63 ms per message** (RTX 3050).
- Multi-hop attacks: **100 %** caught at 3.0 % false alarms (calibrated cut-off: ≤ 1.8 % on every seed). A stateless model held to the same 5 % false-alarm budget catches **4.3 %**, so the gain is **+96 points**.
- Evasive attacker (obfuscated, split, Unicode, paraphrased, delayed): **100 %** at 0.4 % false alarms.
- Live LLM agent (AgentDojo, qwen2.5 7B): attack success **15.3 % → 0 %**, at a cost of 1 of 39 benign tasks.
- Team-written stories: 35–45 % before the tampering checks, **95 %** after, with no retraining (checks designed after seeing these misses).
- Remaining limits: items the agent must decode (25 %), StateAttack false alarms 10 %, and two of the benchmark sets are template-generated.

## 10. Where things are in the code
| Part | File |
|---|---|
| The tap / API | `backend/api/routes.py`, `backend/main.py` |
| Decision logic and tiers | `backend/core/shield.py` |
| Session memory | `backend/core/session.py`, `backend/core/store.py` |
| Signals and tampering checks | `backend/core/features.py` |
| Classifier | `backend/core/detector.py`, model in `artifacts/mapis_detector` |
| Agents (LangGraph / AutoGen) | `backend/agents/graph.py`, `backend/agents/autogen_testbed.py`, `backend/agents/testbed.py` |
| Dashboard | `frontend/src/App.jsx` |
| Benchmarks | `scripts/benchmark.py`, data in `data/mapis_bench/` |
