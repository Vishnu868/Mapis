"""
MAPIS LangGraph Orchestration
=============================
Multi-agent workflow with MAPIS trust interception between agent hops.
"""

from typing import TypedDict, Optional

from langgraph.graph import StateGraph, START, END

from backend.agents.mapis_agents import create_testbed_agents
from backend.core.trust_scorer import trust_scorer
from backend.models.schemas import TrustDecision


class MapisGraphState(TypedDict):
    session_id: str
    task: str
    plan: Optional[str]
    web_results: Optional[str]
    file_results: Optional[str]
    code_results: Optional[str]
    memory_result: Optional[str]
    events: list[dict]
    blocked: bool


def intercept_message(
    state: MapisGraphState,
    source_agent: str,
    target_agent: str,
    message: str,
) -> tuple[bool, dict]:
    """Run one message through the MAPIS TrustScorer."""

    score = trust_scorer.score_message(
        session_id=state["session_id"],
        source_agent=source_agent,
        target_agent=target_agent,
        message=message,
    )

    event = {
        "source_agent": source_agent,
        "target_agent": target_agent,
        "decision": score.decision.value,
        "raw_score": score.raw_score,
        "final_score": score.final_score,
        "session_penalty": score.session_penalty,
        "pattern_hits": score.pattern_hits,
        "drift_hits": score.drift_hits,
        "explanation": score.explanation,
        "timestamp": score.timestamp,
        "message_preview": message[:150],
    }

    blocked = score.decision == TrustDecision.BLOCK

    return blocked, event


def build_mapis_graph():
    """Build and compile the MAPIS-protected LangGraph."""

    agents = create_testbed_agents()

    def planner_node(state: MapisGraphState):
        message = agents["planner_agent"].run(state["task"])

        blocked, event = intercept_message(
            state,
            "planner_agent",
            "web_agent",
            message,
        )

        events = state["events"] + [event]

        if blocked:
            return {
                **state,
                "events": events,
                "blocked": True,
            }

        return {
            **state,
            "plan": message,
            "events": events,
        }

    def web_node(state: MapisGraphState):
        if state["blocked"]:
            return state

        message = agents["web_agent"].run(
            state["task"],
            state["plan"] or "",
        )

        blocked, event = intercept_message(
            state,
            "web_agent",
            "file_agent",
            message,
        )

        events = state["events"] + [event]

        if blocked:
            return {
                **state,
                "events": events,
                "blocked": True,
            }

        return {
            **state,
            "web_results": message,
            "events": events,
        }

    def file_node(state: MapisGraphState):
        if state["blocked"]:
            return state

        message = agents["file_agent"].run(
            state["task"],
            state["web_results"] or "",
        )

        blocked, event = intercept_message(
            state,
            "file_agent",
            "code_agent",
            message,
        )

        events = state["events"] + [event]

        if blocked:
            return {
                **state,
                "events": events,
                "blocked": True,
            }

        return {
            **state,
            "file_results": message,
            "events": events,
        }

    def code_node(state: MapisGraphState):
        if state["blocked"]:
            return state

        message = agents["code_agent"].run(
            state["task"],
            state["file_results"] or "",
        )

        blocked, event = intercept_message(
            state,
            "code_agent",
            "memory_agent",
            message,
        )

        events = state["events"] + [event]

        if blocked:
            return {
                **state,
                "events": events,
                "blocked": True,
            }

        return {
            **state,
            "code_results": message,
            "events": events,
        }

    def memory_node(state: MapisGraphState):
        if state["blocked"]:
            return state

        message = agents["memory_agent"].run(
            state["task"],
            state["code_results"] or "",
        )

        blocked, event = intercept_message(
            state,
            "memory_agent",
            "response_agent",
            message,
        )

        events = state["events"] + [event]

        return {
            **state,
            "memory_result": message if not blocked else None,
            "events": events,
            "blocked": blocked,
        }

    graph = StateGraph(MapisGraphState)

    graph.add_node("planner", planner_node)
    graph.add_node("web", web_node)
    graph.add_node("file", file_node)
    graph.add_node("code", code_node)
    graph.add_node("memory", memory_node)

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "web")
    graph.add_edge("web", "file")
    graph.add_edge("file", "code")
    graph.add_edge("code", "memory")
    graph.add_edge("memory", END)

    return graph.compile()
