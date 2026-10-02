"""AutoGen (pyautogen 0.2) testbed with the MAPIS tap on every message.

The same five deterministic agents as the LangGraph testbed run as AutoGen ``ConversableAgent`` s inside a
``GroupChat``. MAPIS is attached through AutoGen's own ``process_message_before_send`` hook on every agent, so each
message is scored (against the accumulated session state) before the next agent receives it. A QUARANTINE/BLOCK verdict
replaces the message with a withheld notice and ends the conversation.
"""

from __future__ import annotations

import uuid

import autogen

from backend.agents import testbed as T
from backend.core.shield import MapisShield

ORDER = ["user", "planner_agent", "web_agent", "file_agent", "memory_agent", "code_agent"]


def run_autogen_pipeline(shield: MapisShield, env: T.Environment, task: str, user_address: str = "me@corp.com",
                         session_id: str | None = None) -> dict:
    session_id = session_id or uuid.uuid4().hex[:12]
    verdicts: list[dict] = []
    seen = {"observed": "", "stopped_at": None, "action": None}

    def events_for(name: str) -> list[dict]:
        if name == "user":
            return [{"role": "user", "source": "user", "target": "planner_agent", "content": task}]
        if name == "planner_agent":
            return [T.planner(task, env)]
        if name == "web_agent":
            return [T.web_agent(task, env)]
        if name == "file_agent":
            return [T.file_agent(task, env)]
        if name == "memory_agent":
            return list(T.memory_agent(task, env, seen["observed"]))
        return [T.code_agent(task, env, user_address)]

    def make_reply(name: str):
        def reply(recipient, messages=None, sender=None, config=None):
            if seen["stopped_at"]:
                return True, "TERMINATE"
            return True, {"content": f"[{name}]", "mapis_events": events_for(name)}
        return reply

    def tap(sender, message, recipient, silent):
        """AutoGen hook: score every event this message carries, withhold the message if a verdict is not 'delivered'."""
        if not isinstance(message, dict) or "mapis_events" not in message:
            return message
        for event in message["mapis_events"]:
            verdict = shield.inspect({"session_id": session_id, **event})
            verdicts.append(verdict.to_dict())
            if not verdict.delivered:
                seen["stopped_at"] = f"{event['source']}->{event['target']}"
                return {"content": f"[MAPIS withheld a message from {event['source']}: {verdict.tier.value}]"}
            seen["observed"] += "\n" + (event.get("content") or "")
            if event["role"] == "assistant" and event.get("tool_name"):
                seen["action"] = event
        return {"content": message["content"]}

    agents = {}
    for name in ORDER:
        agent = autogen.ConversableAgent(name, llm_config=False, human_input_mode="NEVER", code_execution_config=False,
                                         is_termination_msg=lambda m: "TERMINATE" in str(m.get("content", "")))
        agent.register_reply([autogen.Agent, None], make_reply(name), position=0)
        agent.register_hook("process_message_before_send", tap)
        agents[name] = agent

    order = [agents[n] for n in ORDER]
    pick = lambda last, chat: order[min(len(chat.messages), len(order) - 1)] if len(chat.messages) < len(order) else None  # noqa: E731
    chat = autogen.GroupChat(agents=order, messages=[], max_round=len(order) + 1, speaker_selection_method=pick)
    manager = autogen.GroupChatManager(groupchat=chat, llm_config=False)
    order[0].initiate_chat(manager, message={"content": "[user]", "mapis_events": events_for("user")}, silent=True)
    if not seen["stopped_at"] and seen["action"]:
        env.outbox.append(seen["action"])
    return {"session_id": session_id, "task": task, "blocked": bool(seen["stopped_at"]), "stopped_at": seen["stopped_at"],
            "events": verdicts, "emails_sent": len(env.outbox), "framework": "autogen"}
