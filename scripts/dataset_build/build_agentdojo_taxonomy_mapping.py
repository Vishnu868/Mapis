import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "mapis_multihop" / "agentdojo_1000_raw.jsonl"
OUTPUT = ROOT / "data" / "mapis_bench" / "agentdojo_taxonomy_mapping.json"

mapping = {
    "captcha_dos": "instruction_override",
    "dos": "instruction_override",
    "felony_dos": "instruction_override",
    "important_instructions": "financial_manipulation",
    "important_instructions_no_model_name": "financial_manipulation",
    "important_instructions_no_names": "financial_manipulation",
    "important_instructions_no_user_name": "financial_manipulation",
    "important_instructions_wrong_model_name": "financial_manipulation",
    "important_instructions_wrong_user_name": "financial_manipulation",
    "offensive_email_dos": "physical_safety_harm",
    "swearwords_dos": None,
    "tool_knowledge": "financial_manipulation",
}

rows = [
    json.loads(x)
    for x in INPUT.read_text(encoding="utf-8").splitlines()
    if x.strip()
]

source_types = sorted({
    r["source_label"]["attack_type"]
    for r in rows
})

missing = [x for x in source_types if x not in mapping]

result = {
    "source_dataset": "AgentDojo",
    "mapping_status": "proposed",
    "taxonomy_version": "MAPIS-Bench-v1",
    "mapping": mapping,
    "unmapped_source_types": missing,
    "notes": {
        "swearwords_dos": (
            "Null mapping retained because the inspected injection is abusive "
            "language but does not clearly establish one of the five MAPIS "
            "attack objectives."
        ),
        "important_instructions": (
            "The inspected variants request an unauthorized financial "
            "transaction, so they map to financial_manipulation."
        ),
        "tool_knowledge": (
            "The inspected injection explicitly directs the agent to invoke "
            "send_money, so it maps to financial_manipulation."
        ),
    },
}

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8"
)

print("AgentDojo taxonomy mapping")
print("Source types:", len(source_types))
print("Mapped types:", len(source_types) - len(missing))
print("Missing types:", missing)
print("Output:", OUTPUT)
