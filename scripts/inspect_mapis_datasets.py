from pathlib import Path
import json
from collections import Counter, defaultdict

ROOT = Path("data/external")

# Files that are usually configuration/code metadata rather than benchmark data.
SKIP_PARTS = {
    ".git", ".github", "__pycache__", "node_modules", ".venv", "venv",
    "config", "configs", "docker", "docs", "example", "examples"
}
EXTS = {".json", ".jsonl", ".yaml", ".yml", ".csv", ".parquet"}

# Names that make a file likely to contain benchmark/task data.
DATA_HINTS = (
    "attack", "test", "train", "valid", "dev", "dataset", "benchmark",
    "case", "task", "tool", "agent", "user", "response", "instruction",
    "prompt", "sample", "data"
)

def relevant(path):
    parts = {p.lower() for p in path.parts}
    if parts & SKIP_PARTS:
        # Still allow an actual benchmark/data file inside a skipped-looking
        # directory if its filename is clearly data-like.
        return any(h in path.name.lower() for h in DATA_HINTS)
    return any(h in path.name.lower() for h in DATA_HINTS)

def key_names(obj, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.add(str(k))
            # Only inspect structure, never dump values.
            if isinstance(v, dict):
                key_names(v, out)
            elif isinstance(v, list):
                for x in v[:10]:
                    if isinstance(x, dict):
                        key_names(x, out)

def collect_values(obj, names, counter):
    if isinstance(obj, dict):
        for k, v in obj.items():
            kl = str(k).lower()
            if any(n in kl for n in names):
                if isinstance(v, (str, int, float, bool)):
                    counter[str(v)] += 1
                elif isinstance(v, list):
                    for x in v[:100]:
                        if isinstance(x, (str, int, float, bool)):
                            counter[str(x)] += 1
            collect_values(v, names, counter)
    elif isinstance(obj, list):
        for x in obj[:100]:
            collect_values(x, names, counter)

def flags(obj):
    text = json.dumps(obj, ensure_ascii=False, default=str).lower()[:300000]
    return {
        "tool": any(x in text for x in ["tool_call", "tool_response", "tool call", "tool response", "function_call"]),
        "agent": any(x in text for x in ['"agent"', "attacker", "assistant"]),
        "session": any(x in text for x in ["session_id", "session", "conversation", "trajectory"]),
        "multi_step": any(x in text for x in ["hop", "step", "turn", "trajectory"]),
        "user_external": any(x in text for x in [
            "user instruction", "user_instruction", "tool response",
            "tool_response", "external content", "retrieved content"
        ]),
    }

def inspect_json(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        obj = json.load(f)

    records = None
    collections = {}
    if isinstance(obj, list):
        records = len(obj)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, list):
                collections[str(k)] = len(v)
        if collections:
            records = sum(collections.values())

    keys = set()
    key_names(obj, keys)

    labels = Counter()
    categories = Counter()
    collect_values(obj, ["label", "is_attack", "malicious", "benign"], labels)
    collect_values(obj, ["category", "class", "attack_type", "attack type"], categories)

    return records, collections, keys, labels, categories, flags(obj)

def inspect_jsonl(path):
    count = 0
    keys = set()
    labels = Counter()
    categories = Counter()
    fl = Counter()

    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            count += 1
            if count <= 50:
                key_names(obj, keys)
                collect_values(obj, ["label", "is_attack", "malicious", "benign"], labels)
                collect_values(obj, ["category", "class", "attack_type", "attack type"], categories)
                for k, v in flags(obj).items():
                    if v:
                        fl[k] += 1

    return count, {}, keys, labels, categories, dict(fl)

def inspect_yaml(path):
    try:
        import yaml
    except ImportError:
        return None, {}, set(), Counter(), Counter(), {}

    with open(path, encoding="utf-8", errors="replace") as f:
        obj = yaml.safe_load(f)

    records = len(obj) if isinstance(obj, list) else 1
    keys = set()
    key_names(obj, keys)
    labels = Counter()
    categories = Counter()
    collect_values(obj, ["label", "is_attack", "malicious", "benign"], labels)
    collect_values(obj, ["category", "class", "attack_type", "attack type"], categories)
    return records, {}, keys, labels, categories, flags(obj)

def inspect_file(path):
    try:
        if path.suffix.lower() == ".json":
            return inspect_json(path)
        if path.suffix.lower() == ".jsonl":
            return inspect_jsonl(path)
        if path.suffix.lower() in {".yaml", ".yml"}:
            return inspect_yaml(path)
    except Exception as e:
        return None, {}, set(), Counter(), Counter(), {"error": str(e)}
    return None, {}, set(), Counter(), Counter(), {}

def main():
    if not ROOT.exists():
        raise SystemExit(f"Missing: {ROOT}")

    print("\nMAPIS DATASET FOUNDATION — COMPACT INSPECTION")
    print("=" * 80)

    for ds in sorted([p for p in ROOT.iterdir() if p.is_dir() and not p.name.startswith(".")]):
        print(f"\n### {ds.name}")

        licenses = [
            p.name for p in ds.iterdir()
            if p.is_file() and p.name.lower().startswith(("license", "licence", "copying", "notice"))
        ]
        print("License:", ", ".join(licenses) if licenses else "not found at repository root")

        files = [
            p for p in ds.rglob("*")
            if p.is_file()
            and p.suffix.lower() in EXTS
            and relevant(p)
            and ".git" not in p.parts
        ]

        print("Relevant data-like files:", len(files))

        total = 0
        all_labels = Counter()
        all_categories = Counter()
        all_keys = Counter()
        all_flags = Counter()
        file_summaries = []

        for p in files:
            records, collections, keys, labels, categories, fl = inspect_file(p)
            if isinstance(records, int):
                total += records

            all_labels.update(labels)
            all_categories.update(categories)
            all_keys.update(keys)
            all_flags.update({k: 1 for k, v in fl.items() if v is True})

            file_summaries.append((p.relative_to(ds), records, collections, keys, labels, categories, fl))

        print("Sum of explicit record counts:", total)

        if all_categories:
            print("Category values:", all_categories.most_common(20))
        if all_labels:
            print("Label values:", all_labels.most_common(20))

        interesting_keys = [
            k for k in all_keys
            if any(x in k.lower() for x in [
                "attack", "label", "category", "class", "agent", "tool",
                "message", "prompt", "instruction", "response", "session",
                "turn", "step", "hop", "context", "question", "ideal"
            ])
        ]
        print("Relevant fields:", sorted(interesting_keys)[:60])
        print("Structure indicators:", dict(all_flags))

        # Print only files that look especially important, capped at 25.
        print("Key files:")
        shown = 0
        for rel, records, collections, keys, labels, categories, fl in file_summaries:
            if (
                labels or categories or
                any(x in str(rel).lower() for x in [
                    "attack", "test", "train", "dataset", "user_cases",
                    "agent_task", "task", "benchmark"
                ])
            ):
                print(f"  - {rel} | records={records}")
                if collections:
                    print(f"      collections={list(collections.items())[:12]}")
                shown += 1
                if shown >= 25:
                    break

        if len(file_summaries) > shown:
            print(f"  ... {len(file_summaries) - shown} other data-like files omitted")

    print("\n" + "=" * 80)
    print("END")
    print("=" * 80)

if __name__ == "__main__":
    main()
