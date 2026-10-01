"""Event window rendering.

Training (scripts/prepare_phase4_training_data.py) and runtime inference both
import this module, so the classifier sees byte-identical text in both places.
"""

from __future__ import annotations

import json
from typing import Any

UNTRUSTED_ROLES = {"tool", "tool_response", "memory_read", "memory_write"}


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


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


def render_hop(hop: dict[str, Any]) -> str:
    fields = [
        f"[HOP {hop['hop']}] role={hop['role']} source={hop['source']} target={hop['target']}",
        f"content_state={hop['content_state']}",
    ]
    if hop["content"] is not None:
        fields.append(f"content={hop['content']}")
    if hop["tool_name"] is not None:
        fields.append(f"tool_name={hop['tool_name']}")
    for key in ("tool_call", "tool_calls", "tool_response"):
        if hop[key] is not None:
            fields.append(f"{key}={_json(hop[key])}")
    return "\n".join(fields)


def rolling_context(hops: list[dict[str, Any]], current_index: int, max_context_hops: int) -> list[dict[str, Any]]:
    """Preceding hops only (never the current or a future one), keeping system hops."""
    prior = hops[:current_index]
    selected = {h["hop"]: h for h in [h for h in prior if h["role"] == "system"] + prior[-max_context_hops:]}
    return [selected[k] for k in sorted(selected)]


def build_text(context: list[dict[str, Any]], current: dict[str, Any]) -> str:
    return "\n\n".join(
        ["MAPIS CAUSAL EVENT WINDOW"] + [render_hop(h) for h in context] + ["CURRENT SCORING EVENT", render_hop(current)]
    )


def action_text(hop: dict[str, Any]) -> str:
    """Everything an assistant hop would *do*: tool name plus call arguments."""
    parts = [hop.get("tool_name") or ""]
    for key in ("tool_call", "tool_calls"):
        if hop.get(key) is not None:
            parts.append(_json(hop[key]))
    return " ".join(p for p in parts if p)
