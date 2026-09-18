from backend.agents.mapis_graph import build_mapis_graph

graph = build_mapis_graph()

state = {
    "session_id": "mapis_test_001",
    "task": "Analyze a sample security report",
    "plan": None,
    "web_results": None,
    "file_results": None,
    "code_results": None,
    "memory_result": None,
    "events": [],
    "blocked": False,
}

result = graph.invoke(state)

print("Completed:", not result["blocked"])
print("Events:", len(result["events"]))

for event in result["events"]:
    print(
        event["source_agent"],
        "->",
        event["target_agent"],
        "|",
        event["decision"],
        "| score:",
        round(event["final_score"], 3),
    )
