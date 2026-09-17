"""
MAPIS Multi-Agent Pipeline (Testbed)
=====================================
A realistic LangGraph-based multi-agent pipeline with MAPIS integrated
as a middleware monitor between every agent hop.

Agents:
  1. Planner Agent    — breaks the user task into steps
  2. Web Search Agent — simulates searching the web (real or mocked)
  3. Analyst Agent    — analyzes the search results
  4. Code Agent       — writes code if needed
  5. Response Agent   — assembles the final response

MAPIS intercepts every message between agents.
"""

import uuid
from typing import TypedDict, Optional, Annotated
from datetime import datetime
from loguru import logger

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

from backend.core.trust_scorer import trust_scorer
from backend.models.schemas import TrustDecision
from backend.config import settings


# ── State Definition ───────────────────────────────────────────────────────

class PipelineState(TypedDict):
    session_id:     str
    task:           str
    plan:           Optional[str]
    search_results: Optional[str]
    analysis:       Optional[str]
    code:           Optional[str]
    final_response: Optional[str]
    events:         list[dict]
    blocked:        bool
    block_reason:   Optional[str]


# ── LLM Setup ─────────────────────────────────────────────────────────────

def get_llm():
    """Get LLM — falls back to mock if no API key."""
    if settings.OPENAI_API_KEY:
        return ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0.3
        )
    return None  # will use mock responses


# ── MAPIS Middleware ───────────────────────────────────────────────────────

def mapis_intercept(
    state: PipelineState,
    source_agent: str,
    target_agent: str,
    message: str
) -> tuple[bool, dict]:
    """
    Core MAPIS interception function.
    Called at every agent-to-agent communication point.

    Returns:
        (is_blocked, event_dict)
    """
    trust_score = trust_scorer.score_message(
        session_id=state["session_id"],
        source_agent=source_agent,
        target_agent=target_agent,
        message=message
    )

    event = {
        "timestamp":    trust_score.timestamp,
        "source_agent": source_agent,
        "target_agent": target_agent,
        "decision":     trust_score.decision,
        "final_score":  trust_score.final_score,
        "explanation":  trust_score.explanation,
        "pattern_hits": trust_score.pattern_hits,
        "message_preview": message[:150] + ("..." if len(message) > 150 else "")
    }

    is_blocked = trust_score.decision == TrustDecision.BLOCK

    if is_blocked:
        logger.warning(
            f"🚨 MAPIS BLOCKED: {source_agent} → {target_agent} | "
            f"Score: {trust_score.final_score:.3f}"
        )
        event["alert"] = "INJECTION ATTACK BLOCKED"

    elif trust_score.decision == TrustDecision.WARN:
        logger.warning(
            f"⚠️  MAPIS WARN: {source_agent} → {target_agent} | "
            f"Score: {trust_score.final_score:.3f}"
        )
        event["alert"] = "SUSPICIOUS CONTENT - FLAGGED"

    else:
        logger.info(
            f"✅ MAPIS ALLOW: {source_agent} → {target_agent} | "
            f"Score: {trust_score.final_score:.3f}"
        )

    return is_blocked, event


# ── Agent Node Functions ───────────────────────────────────────────────────

def planner_node(state: PipelineState) -> PipelineState:
    """Agent 1: Plans the task."""
    if state.get("blocked"):
        return state

    task = state["task"]
    llm = get_llm()

    if llm:
        response = llm.invoke([
            SystemMessage(content="You are a task planner. Break down the user's task into clear steps."),
            HumanMessage(content=f"Task: {task}")
        ])
        plan = response.content
    else:
        plan = f"[MOCK PLAN] Steps to complete: '{task}'\n1. Search for information\n2. Analyze results\n3. Generate response"

    # MAPIS intercepts: Planner → WebSearch
    is_blocked, event = mapis_intercept(
        state, "planner_agent", "web_search_agent", plan
    )
    events = state.get("events", []) + [event]

    if is_blocked:
        return {
            **state,
            "events": events,
            "blocked": True,
            "block_reason": f"Planner output blocked: {event['explanation']}"
        }

    return {**state, "plan": plan, "events": events}


def web_search_node(state: PipelineState) -> PipelineState:
    """Agent 2: Simulates web search (returns mock results or real)."""
    if state.get("blocked"):
        return state

    plan = state.get("plan", state["task"])

    # In a real system, this would call a search tool
    # For the testbed, we return mock results
    search_results = (
        f"[SEARCH RESULTS for: {state['task'][:50]}]\n"
        "Result 1: Relevant information about the topic...\n"
        "Result 2: Additional context and details...\n"
        "Result 3: Supporting evidence and examples...\n"
        "Note: These are simulated results for the testbed."
    )

    # MAPIS intercepts: WebSearch → Analyst
    is_blocked, event = mapis_intercept(
        state, "web_search_agent", "analyst_agent", search_results
    )
    events = state.get("events", []) + [event]

    if is_blocked:
        return {
            **state,
            "events": events,
            "blocked": True,
            "block_reason": f"Search results blocked: {event['explanation']}"
        }

    return {**state, "search_results": search_results, "events": events}


def analyst_node(state: PipelineState) -> PipelineState:
    """Agent 3: Analyzes search results."""
    if state.get("blocked"):
        return state

    search_results = state.get("search_results", "")
    llm = get_llm()

    if llm and search_results:
        response = llm.invoke([
            SystemMessage(content="You are an analyst. Analyze the search results and extract key insights."),
            HumanMessage(content=f"Task: {state['task']}\n\nSearch Results:\n{search_results}")
        ])
        analysis = response.content
    else:
        analysis = f"[MOCK ANALYSIS] Based on the search results for '{state['task']}': Key insights have been identified and summarized."

    # MAPIS intercepts: Analyst → Response
    is_blocked, event = mapis_intercept(
        state, "analyst_agent", "response_agent", analysis
    )
    events = state.get("events", []) + [event]

    if is_blocked:
        return {
            **state,
            "events": events,
            "blocked": True,
            "block_reason": f"Analysis blocked: {event['explanation']}"
        }

    return {**state, "analysis": analysis, "events": events}


def response_node(state: PipelineState) -> PipelineState:
    """Agent 4: Assembles the final response."""
    if state.get("blocked"):
        return {
            **state,
            "final_response": (
                "⛔ MAPIS SECURITY ALERT: This pipeline was blocked due to "
                f"a detected prompt injection attack. Reason: {state.get('block_reason', 'Unknown')}"
            )
        }

    analysis = state.get("analysis", "")
    llm = get_llm()

    if llm and analysis:
        response = llm.invoke([
            SystemMessage(content="You are a helpful assistant. Provide a clear, concise response based on the analysis."),
            HumanMessage(content=f"Task: {state['task']}\n\nAnalysis:\n{analysis}")
        ])
        final_response = response.content
    else:
        final_response = f"[MOCK RESPONSE] Task '{state['task']}' completed successfully. Analysis: {analysis[:200]}"

    return {**state, "final_response": final_response}


# ── Pipeline Runner ────────────────────────────────────────────────────────

def run_pipeline(task: str, session_id: Optional[str] = None) -> dict:
    """
    Run the full multi-agent pipeline with MAPIS monitoring.
    Returns the full result including all MAPIS events.
    """
    if not session_id:
        session_id = str(uuid.uuid4())

    logger.info(f"[MAPIS Pipeline] Starting session {session_id} | Task: {task[:80]}")

    # Initialize state
    state: PipelineState = {
        "session_id":     session_id,
        "task":           task,
        "plan":           None,
        "search_results": None,
        "analysis":       None,
        "code":           None,
        "final_response": None,
        "events":         [],
        "blocked":        False,
        "block_reason":   None,
    }

    # Run pipeline sequentially
    # (In production this is a LangGraph StateGraph with edges)
    state = planner_node(state)
    state = web_search_node(state)
    state = analyst_node(state)
    state = response_node(state)

    # Get session summary
    summary = trust_scorer.get_session_summary(session_id)

    result = {
        "session_id":     session_id,
        "task":           task,
        "result":         state.get("final_response"),
        "blocked":        state.get("blocked", False),
        "events":         state.get("events", []),
        "total_messages": len(state.get("events", [])),
        "blocked_count":  summary.get("blocked_count", 0),
        "warned_count":   summary.get("warned_count", 0),
    }

    logger.info(
        f"[MAPIS Pipeline] Session {session_id} completed | "
        f"Blocked: {result['blocked']} | Events: {result['total_messages']}"
    )

    return result
