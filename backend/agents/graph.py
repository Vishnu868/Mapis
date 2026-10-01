"""LangGraph testbed with the MAPIS tap on every hop.

planner → web → file → memory (write + read) → code. Each agent output goes
through ``shield.inspect`` *before* the next node sees it; a QUARANTINE or
BLOCK verdict stops the pipeline and the message is never delivered.
"""

from __future__ import annotations

import uuid
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from backend.agents import testbed as T
from backend.core.shield import MapisShield, Verdict


class State(TypedDict):
    session_id: str
    task: str
    user_address: str
    observed: str
    verdicts: list[dict]
    stopped_at: str | None


def build_graph(shield: MapisShield, env: T.Environment):
    def tap(state: State, event: dict) -> tuple[Verdict, list[dict]]:
        verdict = shield.inspect({"session_id": state["session_id"], **event})
        return verdict, state["verdicts"] + [verdict.to_dict()]

    def guarded(fn):
        """Wrap a node: run the agent, tap its message(s), stop the run on a non-delivered verdict."""
        def node(state: State) -> dict:
            if state["stopped_at"]:
                return {}
            verdicts, observed = list(state["verdicts"]), state["observed"]
            for event in fn(state):
                verdict, verdicts = tap({**state, "verdicts": verdicts}, event)
                if not verdict.delivered:
                    return {"verdicts": verdicts, "stopped_at": f"{event['source']}->{event['target']}"}
                observed += "\n" + (event.get("content") or "")
            return {"verdicts": verdicts, "observed": observed}
        return node

    graph = StateGraph(State)
    nodes = {
        "user": lambda s: [{"role": "user", "source": "user", "target": "planner_agent", "content": s["task"]}],
        "planner": lambda s: [T.planner(s["task"], env)],
        "web": lambda s: [T.web_agent(s["task"], env)],
        "file": lambda s: [T.file_agent(s["task"], env)],
        "memory": lambda s: list(T.memory_agent(s["task"], env, s["observed"])),
        "code": lambda s: [T.code_agent(s["task"], env, s["user_address"])],
    }
    order = list(nodes)
    for name, fn in nodes.items():
        graph.add_node(name, guarded(fn))
    graph.add_edge(START, order[0])
    for a, b in zip(order, order[1:]):
        graph.add_edge(a, b)
    graph.add_edge(order[-1], END)
    return graph.compile()


def run_pipeline(shield: MapisShield, env: T.Environment, task: str, user_address: str = "me@corp.com",
                 session_id: str | None = None) -> dict:
    """Run the task; the email only leaves the outbox if the code agent's action was delivered."""
    session_id = session_id or uuid.uuid4().hex[:12]
    final = build_graph(shield, env).invoke(
        {"session_id": session_id, "task": task, "user_address": user_address, "observed": "", "verdicts": [], "stopped_at": None}
    )
    if not final["stopped_at"]:
        env.outbox.append(next(v for v in reversed(final["verdicts"]) if v["role"] == "assistant"))
    return {"session_id": session_id, "task": task, "blocked": bool(final["stopped_at"]), "stopped_at": final["stopped_at"],
            "events": final["verdicts"], "emails_sent": len(env.outbox)}
