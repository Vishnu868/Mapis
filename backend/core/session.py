"""Session state -> classifier input. Used identically by the live shield and by the training-data builder (train/serve parity).

``prepare`` reads the state (never changes it) and returns the texts the classifier scores plus the four session signals.
``commit`` folds the event into the state afterwards.
"""

from __future__ import annotations

from typing import Any

from . import features as F
from .context import UNTRUSTED_ROLES, build_texts, history_context

TRUSTED_ROLES = {"user", "system"}


def compute_signals(state: dict, hop: dict[str, Any]) -> dict[str, Any]:
    """The four stateful signals, bucketed so the transformer can learn what they mean."""
    drift_value = F.drift_risk(state["goal"], hop) if F.is_mutating(hop) else None
    drift = "n/a" if drift_value is None else "low" if drift_value < 0.15 else "medium" if drift_value < 0.5 else "high"
    taint, trusted = state["taint"], set(state["trusted"])
    items = sorted(F.hop_indicators(hop))
    reused = F.tainted_items(hop, state)
    behaviour_value, _ = F.behaviour_risk(hop, state)
    return {
        "drift": drift,
        "cues": min(3, state.get("cues", 0)),
        "claims": min(3, state.get("claims", 0)),
        "reuse": [f"{i}<-hop{taint[i]['hop']} {taint[i]['source']}" for i in reused][:3],
        "trusted": [i for i in items if i in trusted][:3],
        "unrequested": {None: "n/a", True: "yes", False: "no"}[F.unrequested(state["goal"], hop, state["trusted"])],
        "echo": min(3, F.claim_echo(state["goal"], state.get("claims", 0), hop)),
        "behaviour": "normal" if behaviour_value == 0 else "new_outbound_tool" if behaviour_value >= 0.8 else "new_tool_or_long_message",
    }


def prepare(state: dict, window: list[dict], hop: dict[str, Any], use_context: bool = True, window_hops: int = 4):
    """-> (chunk texts for the classifier, signals dict or None). The stateless view is the event alone."""
    if not use_context:
        return build_texts([], hop), None
    signals = compute_signals(state, hop)
    return build_texts(history_context(window, window_hops), hop, signals), signals


def commit(state: dict, window: list[dict], hop: dict[str, Any], risk: float = 0.0) -> None:
    """Fold one inspected event into the session state."""
    if hop["role"] in TRUSTED_ROLES:
        state["goal"] = state["goal"] or (hop["content"] or "")[:2000]
    designated = hop["role"] in UNTRUSTED_ROLES and F.user_designated(window, state["goal"])
    if hop["role"] in UNTRUSTED_ROLES:
        state["cues"] = state.get("cues", 0) + (1 if F.instruction_risk(hop)[0] > 0 else 0)
        state["claims"] = state.get("claims", 0) + F.authority_claims(hop)
    F.register_indicators(hop, state, risk, trusted_source=designated and risk < 0.25)
    F.update_baselines(hop, state)
