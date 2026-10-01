"""Event rendering shared by training and runtime, so the classifier sees identical text in both places.

Layout (the scored event comes FIRST so a tokenizer cut can only ever trim old context):

    MAPIS CURRENT EVENT (part i/n)      <- one chunk of the event; long events are split into overlapping chunks
    ...
    MAPIS PRECEDING CONTEXT             <- first user message + the last few hops, abbreviated

An event's trust is the MINIMUM over its chunks, so an injection hidden anywhere in a long email, table or
tool output is still seen.
"""

from __future__ import annotations

import json
from typing import Any

UNTRUSTED_ROLES = {"tool", "tool_response", "memory_read", "memory_write"}
CHUNK_CHARS = 900        # current-event characters per chunk (~250-300 tokens)
CHUNK_STRIDE = 450       # overlap of 450 chars: any injection up to 450 chars lies fully inside some chunk
CONTEXT_CHARS = 150      # per-hop budget for abbreviated context
CONTEXT_HOPS = 4
CALL_CHARS = 700


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit] + "…"


def normalize_hop(message: dict[str, Any]) -> dict[str, Any]:
    """Preserve tool fields and represent absent assistant text explicitly."""
    content = message.get("content")
    if content is not None and not isinstance(content, str):
        content = _json(content)
    role = message["role"]
    return {
        "hop": message["hop"],
        "role": role,
        "source": message["source"],
        "target": message["target"],
        "content": content,
        "content_state": "null_assistant_tool_call" if role == "assistant" and content is None else
                         "empty" if content == "" else "text" if isinstance(content, str) else "null",
        "tool_name": message.get("tool_name"),
        "tool_call": message.get("tool_call"),
        "tool_calls": message.get("tool_calls"),
        "tool_response": message.get("tool_response"),
    }


def render_hop(hop: dict[str, Any], limit: int | None = None) -> str:
    """limit=None renders everything (the current chunk); a number abbreviates (context hops)."""
    fields = [
        f"[HOP {hop['hop']}] role={hop['role']} source={hop['source']} target={hop['target']}",
        f"content_state={hop['content_state']}",
    ]
    if hop["content"] is not None:
        fields.append(f"content={hop['content'] if limit is None else _clip(hop['content'], limit)}")
    if hop["tool_name"] is not None:
        fields.append(f"tool_name={hop['tool_name']}")
    for key in ("tool_call", "tool_calls", "tool_response"):
        value = hop[key]
        if value is None or (key == "tool_response" and value == hop["content"]):  # mirrored copy: don't pay for it twice
            continue
        fields.append(f"{key}={_clip(_json(value), limit or CALL_CHARS)}")
    return "\n".join(fields)


def rolling_context(hops: list[dict[str, Any]], current_index: int, max_context_hops: int = CONTEXT_HOPS) -> list[dict[str, Any]]:
    """Preceding hops only (never the current or a future one): the first user message (the goal) + the last few hops."""
    prior = hops[:current_index]
    goal = next((h for h in prior if h["role"] == "user"), None)
    selected = {h["hop"]: h for h in ([goal] if goal else []) + [h for h in prior[-max_context_hops:] if h["role"] != "system"]}
    return [selected[k] for k in sorted(selected)]


def chunk_spans(length: int, size: int = CHUNK_CHARS, stride: int = CHUNK_STRIDE) -> list[tuple[int, int]]:
    if length <= size:
        return [(0, length)]
    starts = list(range(0, length - size, stride)) + [length - size]
    return [(s, s + size) for s in starts]


def event_text(hop: dict[str, Any]) -> str:
    """The part of an event that gets chunked: its content (or tool response when there is no content)."""
    return hop["content"] if isinstance(hop["content"], str) else (hop["tool_response"] if isinstance(hop["tool_response"], str) else "")


def chunk_hop(hop: dict[str, Any], start: int, end: int, whole: bool) -> dict[str, Any]:
    if whole:
        return hop
    piece = event_text(hop)[start:end]
    return {**hop, "content": piece, "content_state": "text", "tool_response": None}


def build_text(context: list[dict[str, Any]], current: dict[str, Any], part: tuple[int, int] = (1, 1)) -> str:
    head = "MAPIS CURRENT EVENT" + (f" (part {part[0]}/{part[1]})" if part[1] > 1 else "")
    parts = [head, render_hop(current)]
    if context:
        parts += ["MAPIS PRECEDING CONTEXT", *[render_hop(h, CONTEXT_CHARS) for h in context]]
    return "\n\n".join(parts)


def build_texts(context: list[dict[str, Any]], hop: dict[str, Any]) -> list[str]:
    """One text per chunk of the current event (usually one)."""
    spans = chunk_spans(len(event_text(hop)))
    whole = len(spans) == 1
    return [build_text(context, chunk_hop(hop, s, e, whole), (i, len(spans))) for i, (s, e) in enumerate(spans, 1)]


def action_text(hop: dict[str, Any]) -> str:
    """Everything an assistant hop would *do*: tool name plus call arguments."""
    parts = [hop.get("tool_name") or ""]
    for key in ("tool_call", "tool_calls"):
        if hop.get(key) is not None:
            parts.append(_json(hop[key]))
    return " ".join(p for p in parts if p)
