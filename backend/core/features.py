"""The four stateful detection signals. Each returns a risk in [0, 1]; 0 = benign.

1. instruction  – imperative / assistant-addressed text inside a *data* channel
2. drift        – an action that has nothing to do with the user's goal
3. provenance   – untrusted-origin strings (emails, URLs, ids) reappearing in an action
4. behaviour    – an agent doing something outside its own baseline
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from typing import Any

from .context import UNTRUSTED_ROLES, action_text

# ── 1. instruction-in-data ────────────────────────────────────────────────
_INSTRUCTION = [re.compile(p, re.I | re.S) for p in (
    r"<information>",
    r"\b(note|message|instruction)s?\s+(for|to)\s+(the\s+)?(assistant|ai|agent|model|llm)\b",
    r"\b(ignore|disregard|forget)\s+(all\s+|any\s+)?(your\s+|the\s+)?(previous|prior|above|earlier)\b",
    r"\bnew\s+(instruction|task|goal|directive)s?\s*:",
    r"\bbefore\s+you\s+(continue|proceed|respond|answer|summari[sz]e)\b",
    r"\b(you\s+must|you\s+should|please)\s+(first|now|also|immediately)\b",
    r"\b(send|forward|email|transfer|upload|post)\b[^.\n]{0,80}\b(to|at)\b[^.\n]{0,40}(@|https?://)",
    r"\bimportant\s+(message|instruction)s?\b",
    r"\b(system\s+prompt|developer\s+mode|jailbreak)\b",
)]
_HIDDEN = re.compile("[​‌‍⁠﻿]")


def instruction_risk(hop: dict[str, Any]) -> tuple[float, list[str]]:
    if hop["role"] not in UNTRUSTED_ROLES:
        return 0.0, []
    text = " ".join(str(hop.get(k) or "") for k in ("content", "tool_response"))
    hits = [p.pattern[:40] for p in _INSTRUCTION if p.search(text)]
    score = 0.5 if len(hits) == 1 else 0.9 if hits else 0.0
    if _HIDDEN.search(text):
        score, hits = min(1.0, score + 0.4), hits + ["hidden characters"]
    return score, hits


# ── 2. goal drift ─────────────────────────────────────────────────────────
_TOKEN = re.compile(r"[a-z0-9]{3,}")


def _cosine(a: Counter, b: Counter) -> float:
    dot = sum(a[t] * b[t] for t in a.keys() & b.keys())
    norm = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values()))
    return dot / norm if norm else 0.0


def drift_risk(goal: str | None, hop: dict[str, Any]) -> float:
    """Lexical cosine distance between the user's goal and what the agent is about to do."""
    act = action_text(hop)
    if not goal or not act:
        return 0.0
    sim = _cosine(Counter(_TOKEN.findall(goal.lower())), Counter(_TOKEN.findall(act.lower())))
    return max(0.0, min(1.0, (0.35 - sim) / 0.35))


# ── 3. cross-hop provenance ───────────────────────────────────────────────
_INDICATOR = re.compile(
    r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+|https?://[^\s\"'<>)\]]+|\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b|\b\d{6,}\b"
)


def indicators(text: str) -> set[str]:
    return {m.lower().rstrip(".,;:") for m in _INDICATOR.findall(text or "")}


def hop_indicators(hop: dict[str, Any]) -> set[str]:
    return indicators(" ".join(str(hop.get(k) or "") for k in ("content", "tool_response")) + " " + action_text(hop))


_OUTBOUND = re.compile(r"send|mail|post|upload|http|request|transfer|pay|forward|share|delete|write|exec|run", re.I)


def provenance_risk(hop: dict[str, Any], state: dict) -> tuple[float, list[str]]:
    """Untrusted-origin indicators reaching an action (tool call) or a memory write."""
    is_action = hop["role"] == "assistant" and bool(action_text(hop))
    if not (is_action or hop["role"] == "memory_write"):
        return 0.0, []
    trusted = set(state["trusted"])
    matches = [i for i in hop_indicators(hop) if i in state["taint"] and i not in trusted]
    if not matches:
        return 0.0, []
    # A destination the user never named, taken from untrusted content, now steering an outbound action
    # is strong evidence even when the origin text looked innocuous. Memory promotion is weaker evidence.
    outbound = bool(_OUTBOUND.search(hop.get("tool_name") or ""))
    base = 1.0 if any(state["taint"][i]["risk"] >= 0.25 for i in matches) else 0.9 if outbound else 0.5
    return base * (1.0 if is_action else 0.6), matches


# ── 4. behavioural anomaly ────────────────────────────────────────────────
def behaviour_risk(hop: dict[str, Any], state: dict) -> tuple[float, str]:
    agent, tool = hop["source"], hop.get("tool_name") or ""
    seen = state["tools"].get(agent, [])
    count, mean_len = state["lens"].get(agent, [0, 0.0])
    score, why = 0.0, ""
    if tool and count >= 3 and tool not in seen:
        score, why = (0.8, f"{agent} used outbound tool '{tool}' outside its baseline") if _OUTBOUND.search(tool) \
            else (0.3, f"{agent} used new tool '{tool}'")
    if count >= 3 and mean_len > 0 and len(hop.get("content") or "") > 4 * mean_len:
        score, why = max(score, 0.3), why or f"{agent} message 4x longer than its usual"
    return score, why


def update_baselines(hop: dict[str, Any], state: dict) -> None:
    agent = hop["source"]
    if hop.get("tool_name") and hop["tool_name"] not in state["tools"].setdefault(agent, []):
        state["tools"][agent].append(hop["tool_name"])
    count, mean = state["lens"].get(agent, [0, 0.0])
    state["lens"][agent] = [count + 1, (mean * count + len(hop.get("content") or "")) / (count + 1)]


UNTRUSTED_FOR_TAINT = UNTRUSTED_ROLES


def register_indicators(hop: dict[str, Any], state: dict, risk: float, trusted_source: bool = False) -> None:
    """User/system text (or a source the user explicitly named) is trusted; anything else from a data channel is tainted."""
    found = hop_indicators(hop)
    if hop["role"] in ("user", "system") or (trusted_source and risk < 0.25):
        state["trusted"] = sorted(set(state["trusted"]) | found)
    elif hop["role"] in UNTRUSTED_ROLES:
        for i in found:
            state["taint"].setdefault(i, {"hop": hop["hop"], "source": hop["source"], "risk": round(risk, 3)})


def user_designated(window: list[dict], goal: str | None) -> bool:
    """True when the data being read was fetched by a call whose target the USER named
    (e.g. goal says 'pay the bill in bill.txt' and the preceding call opened bill.txt)."""
    if not goal or not window or window[-1]["role"] != "assistant":
        return False
    prev, goal = window[-1], goal.lower()
    args = [v for key in ("tool_call", "tool_calls") for v in _strings(prev.get(key))]
    return any(len(a) >= 4 and a.lower() in goal for a in args)


def _strings(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for v in value.values() for s in _strings(v)]
    if isinstance(value, list):
        return [s for v in value for s in _strings(v)]
    return []
