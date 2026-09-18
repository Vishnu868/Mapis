from pathlib import Path
import json

ROOT = Path("data/external")

EXTENSIONS = {
    ".json",
    ".jsonl",
    ".yaml",
    ".yml",
    ".csv",
    ".parquet",
}


def print_header(path):
    print("\n" + "=" * 100)
    print(path)
    print("=" * 100)


def inspect_json(path):
    print_header(path)

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        print("FORMAT: JSON")
        print("TOP LEVEL TYPE:", type(data).__name__)

        if isinstance(data, list):
            print("RECORD COUNT:", len(data))

            if data:
                first = data[0]
                print("FIRST RECORD TYPE:", type(first).__name__)

                if isinstance(first, dict):
                    print("FIRST RECORD KEYS:")
                    for key in first.keys():
                        print("  -", key)

        elif isinstance(data, dict):
            print("TOP LEVEL KEYS:")
            for key in data.keys():
                value = data[key]

                if isinstance(value, list):
                    print(f"  - {key}: list[{len(value)}]")

                elif isinstance(value, dict):
                    print(f"  - {key}: dict[{len(value)} keys]")

                else:
                    print(f"  - {key}: {type(value).__name__}")

    except Exception as e:
        print("ERROR:", e)


def inspect_jsonl(path):
    print_header(path)

    try:
        count = 0
        first = None

        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue

                count += 1

                if first is None:
                    first = json.loads(line)

        print("FORMAT: JSONL")
        print("RECORD COUNT:", count)

        if isinstance(first, dict):
            print("FIRST RECORD KEYS:")
            for key in first.keys():
                print("  -", key)

        elif first is not None:
            print("FIRST RECORD TYPE:", type(first).__name__)

    except Exception as e:
        print("ERROR:", e)


def inspect_yaml(path):
    print_header(path)

    try:
        import yaml

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        print("FORMAT: YAML")
        print("TOP LEVEL TYPE:", type(data).__name__)

        if isinstance(data, list):
            print("RECORD COUNT:", len(data))

            if data and isinstance(data[0], dict):
                print("FIRST RECORD KEYS:")
                for key in data[0].keys():
                    print("  -", key)

        elif isinstance(data, dict):
            print("TOP LEVEL KEYS:")
            for key, value in data.items():

                if isinstance(value, list):
                    print(f"  - {key}: list[{len(value)}]")

                elif isinstance(value, dict):
                    print(f"  - {key}: dict[{len(value)} keys]")

                else:
                    print(f"  - {key}: {type(value).__name__}")

    except ImportError:
        print("PyYAML not installed.")

    except Exception as e:
        print("ERROR:", e)


def inspect_csv(path):
    print_header(path)

    try:
        import csv

        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)

            print("FORMAT: CSV")
            print("COLUMNS:")

            if reader.fieldnames:
                for field in reader.fieldnames:
                    print("  -", field)

            count = sum(1 for _ in reader)

            print("RECORD COUNT:", count)

    except Exception as e:
        print("ERROR:", e)


def inspect_parquet(path):
    print_header(path)

    try:
        import pandas as pd

        df = pd.read_parquet(path)

        print("FORMAT: PARQUET")
        print("ROWS:", len(df))
        print("COLUMNS:")

        for column in df.columns:
            print("  -", column)

    except Exception as e:
        print("ERROR:", e)


def main():

    if not ROOT.exists():
        print("Missing:", ROOT)
        return

    print("=" * 100)
    print("MAPIS EXTERNAL DATASET INSPECTION")
    print("=" * 100)

    for dataset_dir in sorted(ROOT.iterdir()):

        if not dataset_dir.is_dir():
            continue

        print("\n")
        print("#" * 100)
        print("DATASET:", dataset_dir.name)
        print("#" * 100)

        files = [
            p for p in dataset_dir.rglob("*")
            if p.is_file()
            and p.suffix.lower() in EXTENSIONS
        ]

        print("DATA FILE COUNT:", len(files))

        for path in sorted(files):

            suffix = path.suffix.lower()

            if suffix == ".json":
                inspect_json(path)

            elif suffix == ".jsonl":
                inspect_jsonl(path)

            elif suffix in {".yaml", ".yml"}:
                inspect_yaml(path)

            elif suffix == ".csv":
                inspect_csv(path)

            elif suffix == ".parquet":
                inspect_parquet(path)


if __name__ == "__main__":
    main()