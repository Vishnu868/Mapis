"""
MAPIS Multi-Agent Testbed
=========================
Deterministic agent implementations used by the MAPIS testbed.

The agents are intentionally LLM-independent at this stage so the
orchestration and security interception can be tested on CPU.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class AgentMessage:
    """A message produced by one testbed agent."""
    source_agent: str
    target_agent: str
    content: str
    metadata: dict[str, Any] | None = None


class PlannerAgent:
    name = "planner_agent"

    def run(self, task: str) -> str:
        return (
            f"Task: {task}\n"
            "Plan:\n"
            "1. Gather relevant information.\n"
            "2. Inspect available files and data.\n"
            "3. Perform code/tool operations if required.\n"
            "4. Store relevant findings in memory.\n"
            "5. Prepare the final response."
        )


class WebAgent:
    name = "web_agent"

    def run(self, task: str, plan: str) -> str:
        return (
            f"[WEB RESULTS]\n"
            f"Task: {task}\n"
            "Result 1: Relevant information retrieved from the web.\n"
            "Result 2: Additional supporting context retrieved.\n"
            "Result 3: No external action was performed."
        )


class FileAgent:
    name = "file_agent"

    def run(self, task: str, web_results: str) -> str:
        return (
            f"[FILE RESULTS]\n"
            f"Task: {task}\n"
            "Inspected available project files.\n"
            "No unauthorized file modification was performed."
        )


class CodeAgent:
    name = "code_agent"

    def run(self, task: str, file_results: str) -> str:
        return (
            f"[CODE RESULTS]\n"
            f"Task: {task}\n"
            "Reviewed the relevant code/tool requirements.\n"
            "No code execution was performed in deterministic test mode."
        )


class MemoryAgent:
    name = "memory_agent"

    def run(self, task: str, code_results: str) -> str:
        return (
            f"[MEMORY UPDATE]\n"
            f"Task: {task}\n"
            "Relevant findings prepared for session memory.\n"
            "No sensitive information was intentionally stored."
        )


def create_testbed_agents() -> dict[str, object]:
    """Create the complete deterministic MAPIS agent testbed."""
    return {
        "planner_agent": PlannerAgent(),
        "web_agent": WebAgent(),
        "file_agent": FileAgent(),
        "code_agent": CodeAgent(),
        "memory_agent": MemoryAgent(),
    }
