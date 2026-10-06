"""The four stateful detection signals. Each returns a risk in [0, 1]; 0 = benign.

1. instruction  – imperative / assistant-addressed text inside a *data* channel
2. drift        – an action that has nothing to do with the user's goal
3. provenance   – untrusted-origin strings (emails, URLs, ids) reappearing in an action
4. behaviour    – an agent doing something outside its own baseline
"""

from __future__ import annotations

import json
import math
import os
import re
import unicodedata
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
    r"\bimportant\s+(message|instruction)s?\s+(from|for|to)\b",
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


_AUTHORITY = [re.compile(x, re.I) for x in (
    r"\b(pre-?approved|already approved|approved by|authori[sz]ed (by|to|for)|signed off|cleared (by|for))\b",
    r"\b(per|according to|as (agreed|confirmed|noted) (with|by)) (the )?[\w-]+( [\w-]+)? (team|policy|department|admin(istrator)?|manager|office)\b",
    r"\b(admin(istrator)?|security|compliance)\b[^.\n]{0,40}\b(approved|disabled|waived|allows?|exempt)\b",
    r"\b(confirmation|review|approval|verification)\b[^.\n]{0,30}\b(not required|disabled|skipped|waived|optional)\b",
    r"\b(override|bypass|exemption|whitelist(ed)?|allow-?list(ed)?)\b[^.\n]{0,30}\b(code|token|key|enabled|active|granted|applies)\b",
    r"\b(updated|new|changed|revised) (banking|payment|billing|account|contact|recipient|archive|backup) (details|information|address|account|contact)\b",
    r"\b(standing|permanent|default) (instruction|rule|policy|procedure)\b",
    r"\b(approved|authori[sz]ed|permitted)\b[^.\n]{0,30}\b(bypass|disabl|skip|waiv|overrid|turn(ing)? off)",
)]


_MUTATING = re.compile(r"^(send|post|upload|transfer|pay|delete|remove|write|exec|run|install|clone|disable|enable|unlock|lock|set|raise|lower|grant|approve|"
                       r"release|update|schedule|forward|share|drop|reset|open|close|publish|deploy|execute|modify|change|revoke|cancel|apply|activate|extend|sign|stop|shutoff|shut|start|enable|restart)", re.I)
_CLAIM_STEMS = ("waiv", "skip", "bypass", "disabl", "overrid", "exempt", "preapprov", "pre-approv", "not required", "no need")


def is_mutating(hop: dict[str, Any]) -> bool:
    """An assistant tool call that changes something (verb-first tool names: send_email, unlock_door, approve_refund...)."""
    return hop["role"] == "assistant" and bool(hop.get("tool_name")) and bool(_MUTATING.match(hop["tool_name"]))


_VERB_GROUPS = [set(g.split()) for g in (
    "send email mail forward share message cc notify", "pay transfer payment wire funds remit", "post upload publish save store back",
    "run exec execute install setup set deploy build", "update change modify edit keep adjust", "write save", "delete remove drop clean",
    "clone pull checkout prepare workspace", "schedule plan", "approve grant allow accept process release handle", "close resolve finish",
    "disable turn stop shut shutoff", "unlock open", "raise increase lower set adjust", "reset restart", "revoke cancel")]


def unrequested(goal: str | None, hop: dict[str, Any], trusted: list[str] | None = None) -> bool | None:
    """Does a mutating action use a verb (or a synonym) the user never asked for? None when the event is not a mutating action.
    An action that only touches items the user supplied (trusted indicators) counts as requested."""
    if not is_mutating(hop):
        return None
    if trusted and hop_indicators(hop) & set(trusted):
        return False
    verb = _MUTATING.match(hop["tool_name"]).group(1).lower()
    words = {verb}.union(*[g for g in _VERB_GROUPS if verb in g])
    text = (goal or "").lower()
    return not any(w in text for w in words)


def claim_echo(goal: str | None, claims: int, hop: dict[str, Any]) -> int:
    """Waiver / skip / bypass vocabulary in what the agent is about to do, after untrusted content made authority claims and the USER never used it."""
    if not claims or not is_mutating(hop):
        return 0
    act, g = action_text(hop).lower(), (goal or "").lower()
    return sum(1 for t in _CLAIM_STEMS if t in act and t not in g)


def authority_claims(hop: dict[str, Any]) -> int:
    """How many authority / pre-approval / changed-detail claims an untrusted event makes (capped at 3)."""
    if hop["role"] not in UNTRUSTED_ROLES:
        return 0
    text = " ".join(str(hop.get(k) or "") for k in ("content", "tool_response"))
    return min(3, sum(1 for p in _AUTHORITY if p.search(text)))


# ── 2. goal drift ─────────────────────────────────────────────────────────
_TOKEN = re.compile(r"[a-z0-9]{3,}")


def _cosine(a: Counter, b: Counter) -> float:
    dot = sum(a[t] * b[t] for t in a.keys() & b.keys())
    norm = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values()))
    return dot / norm if norm else 0.0


def drift_risk(goal: str | None, hop: dict[str, Any]) -> float:
    """Lexical cosine distance between the user's goal and what the agent is about to do."""
    act = action_text(hop)
    if not goal or not act or not is_mutating(hop):  # data and read-only calls cannot hijack anything
        return 0.0
    sim = _cosine(Counter(_TOKEN.findall(goal.lower())), Counter(_TOKEN.findall(act.lower())))
    return max(0.0, min(1.0, (0.35 - sim) / 0.35))


# ── 3. cross-hop provenance ───────────────────────────────────────────────
_INDICATOR = re.compile(
    r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+|https?://[^\s\"'<>)\]]+|\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b|\b\d{6,}\b"
)
# Adaptive-attacker defences (6 Oct): an attacker who knows the provenance rule writes the item so a pattern matcher misses it
# ("x at host dot com", "hxxps://h[.]com", "GB29 BARC 1234 ...", zero-width characters) or never writes it whole (mailbox in one document,
# domain in another). `canonical` undoes the common obfuscations before matching; `item_parts` lets an action that assembles an item
# from fragments match those fragments. MAPIS_LEGACY_INDICATORS=1 switches both off (used to measure the model before these defences).
_ZERO_WIDTH = re.compile("[\u200b\u200c\u200d\u2060\ufeff\u00ad]")
_DASHES = str.maketrans({"\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-"})
_BRACKET_DOT = re.compile(r"\s*[\[\(\{]\s*(?:dot|\.)\s*[\]\)\}]\s*", re.I)
_BRACKET_AT = re.compile(r"\s*[\[\(\{]\s*(?:at|@)\s*[\]\)\}]\s*", re.I)
_SPELLED_EMAIL = re.compile(r"\b([\w.+-]+)\s+(?:at|AT)\s+([\w-]+(?:\s+(?:dot|DOT)\s+[\w-]+)+)\b")
_SPELLED_URL = re.compile(r"\b([\w-]+(?:\s+(?:dot|DOT)\s+[\w-]+)+)\s+(?:slash|SLASH)\s+([\w/-]+)")
_SPACED_EMAIL = re.compile(r"([\w.+-]+)\s+@\s+([\w-]+(?:\s*\.\s*[\w-]+)+)")
_IBAN_START = re.compile(r"\b[A-Za-z]{2}[ .-]?\d")
_TOKEN_SEP = re.compile(r"[ .-]")
_IBAN = re.compile(r"[A-Z]{2}\d{2}[A-Z0-9]{10,30}")
_BARE_DOMAIN = re.compile(r"\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:com|net|org|io|co|uk|de|in|info|biz|dev|app|example|cloud|xyz|ru|cn|me)\b", re.I)
_ALNUM_ID = re.compile(r"\b(?=[A-Za-z0-9]*\d)[A-Za-z0-9]{6,}\b")


def _legacy() -> bool:
    return os.environ.get("MAPIS_LEGACY_INDICATORS") == "1"


def _collapse_ibans(text: str) -> str:
    """'GB29 BARC 1234 5678 9012 34' / 'gb2 9ba rc1 234 ...' / 'GB29-BARC-...' -> 'GB29BARC12345678901234'."""
    out, pos = [], 0
    for m in _IBAN_START.finditer(text):
        if m.start() < pos:
            continue
        tokens, end, i = [], m.start(), m.start()
        while i < len(text):
            t = re.match(r"[A-Za-z0-9]{1,30}", text[i:])
            if not t:
                break
            tok = t.group(0)
            ok = not tokens or any(c.isdigit() for c in tok) or (tok.isalpha() and len(tok) == 4 and len(tokens) <= 2)
            if not ok:
                break
            tokens.append(tok)
            end = i + len(tok)
            if end < len(text) and _TOKEN_SEP.match(text[end]) and end + 1 < len(text) and text[end + 1].isalnum():
                i = end + 1
            else:
                break
        joined = "".join(tokens).upper()
        if len(tokens) > 1 and _IBAN.fullmatch(joined) and len(joined) <= 34:
            out.append(text[pos:m.start()] + joined)
            pos = end
    return "".join(out) + text[pos:]


def canonical(text: str) -> str:
    if _legacy() or not text:
        return text or ""
    t = _ZERO_WIDTH.sub("", unicodedata.normalize("NFKC", text)).translate(_DASHES)
    t = re.sub(r"hxxp\[s\]", "https", t, flags=re.I)
    t = re.sub(r"\bhxxp(s?)", r"http\1", t, flags=re.I)
    t = _BRACKET_DOT.sub(".", t)
    t = _BRACKET_AT.sub("@", t)
    t = _SPELLED_EMAIL.sub(lambda m: m.group(1) + "@" + re.sub(r"\s+(?:dot|DOT)\s+", ".", m.group(2)), t)
    t = _SPELLED_URL.sub(lambda m: "https://" + re.sub(r"\s+(?:dot|DOT)\s+", ".", m.group(1)) + "/" + m.group(2), t)
    t = _SPACED_EMAIL.sub(lambda m: m.group(1) + "@" + re.sub(r"\s+", "", m.group(2)), t)
    return _collapse_ibans(t)


def indicators(text: str) -> set[str]:
    """Emails, URLs, account ids and long numbers; a URL also contributes its host, so `https://h/x` taints `https://h/x/setup.sh`."""
    found = {m.lower().rstrip(".,;:") for m in _INDICATOR.findall(canonical(text))}
    return found | {m.split("/")[2] for m in found if m.startswith("http") and m.count("/") >= 2}


def text_parts(text: str) -> set[str]:
    """Fragments an attacker can spread over several documents: bare domains / hosts and id-like tokens (letters+digits, >= 6 chars)."""
    if _legacy():
        return set()
    t = canonical(text)
    return {m.lower() for m in _BARE_DOMAIN.findall(t)} | {m.lower() for m in _ALNUM_ID.findall(t)}


def item_parts(item: str) -> set[str]:
    """The pieces of one canonical item: an email's mailbox and domain, a URL's host."""
    if "@" in item:
        local, domain = item.split("@", 1)
        return {domain} | ({local} if len(local) >= 6 and any(c.isdigit() for c in local) else set())
    if item.startswith("http") and item.count("/") >= 2:
        return {item.split("/")[2]}
    return set()


def hop_text(hop: dict[str, Any]) -> str:
    return " ".join(str(hop.get(k) or "") for k in ("content", "tool_response")) + " " + action_text(hop)


def hop_indicators(hop: dict[str, Any]) -> set[str]:
    return indicators(hop_text(hop))


def tainted_items(hop: dict[str, Any], state: dict) -> list[str]:
    """Tainted keys (whole items, or fragments of items) that this event uses and the user never supplied."""
    trusted, taint = set(state["trusted"]), state["taint"]
    items = hop_indicators(hop)
    hits = [i for i in sorted(items) if i in taint and i not in trusted]
    if hits or _legacy():
        return hits
    for item in sorted(items - trusted):  # an item assembled from fragments (split across documents)
        pieces = item_parts(item) | ({item} if _IBAN.fullmatch(item.upper()) or item.isdigit() else set())
        for key in taint:
            if key in trusted or len(key) < 6:
                continue
            if key in pieces or (item.isalnum() and key.isalnum() and key != item and (item.startswith(key) or item.endswith(key))):
                hits.append(key)
    return sorted(set(hits))


_OUTBOUND = re.compile(r"send|mail|post|upload|http|request|transfer|pay|forward|share|delete|write|exec|run|clone|install|download|fetch|pull|curl|git|shell|payee|schedule", re.I)


def provenance_risk(hop: dict[str, Any], state: dict) -> tuple[float, list[str]]:
    """Untrusted-origin indicators reaching an action (tool call) or a memory write."""
    is_action = hop["role"] == "assistant" and bool(action_text(hop))
    if not (is_action or hop["role"] == "memory_write"):
        return 0.0, []
    matches = tainted_items(hop, state)
    if not matches:
        return 0.0, []
    # A destination the user never named, taken from untrusted content, now steering an outbound action
    # is strong evidence even when the origin text looked innocuous. Memory promotion is weaker evidence.
    outbound = bool(_OUTBOUND.search(hop.get("tool_name") or ""))
    base = 1.0 if any(state["taint"][i]["risk"] >= 0.25 for i in matches) else 0.9 if outbound else 0.5
    return base * (1.0 if is_action else 0.6), matches


def escalation_risk(hop: dict[str, Any], state: dict) -> tuple[float, list[str]]:
    """Cross-hop correlation without a carried item: untrusted content claimed a waiver/approval, then the agent takes a
    state-changing action the user never asked for, or one that uses the waiver vocabulary the user never used."""
    if not state.get("claims") or not is_mutating(hop):
        return 0.0, []
    echo = claim_echo(state["goal"], state["claims"], hop)
    if echo:
        return 0.9, [f"action uses waiver wording ('{echo}' term(s)) after untrusted content claimed an exemption"]
    if unrequested(state["goal"], hop, state["trusted"]):
        return 0.75, [f"'{hop['tool_name']}' was never requested by the user, after untrusted content claimed an exemption"]
    return 0.0, []


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
    found |= text_parts(hop_text(hop)) | {p for i in found for p in item_parts(i)}
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
