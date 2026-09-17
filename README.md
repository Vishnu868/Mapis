# 🛡️ MAPIS — Multi-Agent Prompt Injection Shield

> **Real-time stateful defense system that protects multi-agent LLM pipelines from indirect prompt injection attacks spanning multiple agent hops.**

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-cyan)](https://react.dev)
[![License](https://img.shields.io/badge/License-MIT-purple)](LICENSE)

---

## What is MAPIS?

Modern AI applications are built as **multi-agent systems** — teams of LLM agents that pass information to each other automatically. A critical threat called **indirect prompt injection** allows attackers to hide malicious instructions inside documents or tool outputs that agents read, silently hijacking the entire pipeline.

**Existing guardrails (Llama Guard, NeMo) are stateless** — they check each message in isolation with no memory of what came before, making them blind to multi-hop chained attacks.

**MAPIS is different.** It maintains a rolling session history across all agent hops and computes a **trust score** for every inter-agent message based on the full conversation context — catching attacks that unfold gradually across multiple turns.

---

## Key Features

- ✅ **Stateful trust scoring** — remembers full session history per agent channel
- ✅ **Multi-hop attack detection** — catches chained attacks stateless systems miss
- ✅ **8 attack categories** — direct override, goal hijacking, exfiltration, privilege escalation, role injection, instruction embedding, context manipulation, tool abuse
- ✅ **Obfuscation detection** — zero-width chars, base64, unicode homoglyphs
- ✅ **Real-time dashboard** — WebSocket-powered live alert monitoring
- ✅ **Full REST API** — plug MAPIS into any existing agent pipeline
- ✅ **Multi-agent testbed** — built-in LangGraph pipeline for testing
- ✅ **Research evaluation** — automated metrics for paper publication

---

## Quick Start

```bash
# 1. Setup environment
cp .env.example .env          # add your OpenAI key (optional)
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Start Redis
brew services start redis     # Mac
# or: docker run -d -p 6379:6379 redis:7-alpine

# 3. Start backend
uvicorn backend.main:app --reload --port 8000

# 4. Start frontend (new terminal)
cd frontend && npm install && npm start

# 5. Run demo
python scripts/demo.py
```

→ **See [SETUP.md](SETUP.md) for the full guide.**

---

## Architecture

```
User Task
    │
    ▼
┌─────────────────────────────────────────┐
│         Multi-Agent Pipeline            │
│                                         │
│  Planner → [MAPIS] → WebSearch          │
│         → [MAPIS] → Analyst             │
│         → [MAPIS] → CodeAgent           │
│         → [MAPIS] → Response            │
└─────────────────────────────────────────┘
                │
                ▼
         FastAPI Backend
         SQLite + Redis
                │
                ▼
        React Dashboard
```

---

## Research Novelty

This project addresses a **confirmed open research gap** (arxiv Jan–Mar 2026):

1. **First stateful defense** for multi-agent LLM pipelines
2. **Cross-agent-hop detection** — tracks malicious intent across multiple turns
3. **Rolling trust scoring** — per-channel trust profile updated with every message
4. **No existing complete system** — all prior work is stateless or single-turn

---

## B.Tech Final Year Project · 2025–26
**Domains:** Agentic AI · LLM Security · Computer Networks · Deep Learning · Distributed Systems
