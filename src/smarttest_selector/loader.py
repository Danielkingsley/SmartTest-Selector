import csv
import json
from pathlib import Path
from typing import List

from .models import TestCase


def _split_multi(value: str) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split("|") if item.strip()]


def load_testcases(path: str) -> List[TestCase]:
    input_path = Path(path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    if input_path.suffix.lower() == ".json":
        with input_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return [
            TestCase(
                id=str(item["id"]),
                title=item["title"],
                description=item.get("description", ""),
                module=item.get("module", ""),
                tags=item.get("tags", []) or [],
                steps=item.get("steps", []) or [],
            )
            for item in data
        ]

    if input_path.suffix.lower() == ".csv":
        cases: List[TestCase] = []
        with input_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cases.append(
                    TestCase(
                        id=str(row.get("id", "")).strip(),
                        title=str(row.get("title", "")).strip(),
                        description=str(row.get("description", "")).strip(),
                        module=str(row.get("module", "")).strip(),
                        tags=_split_multi(str(row.get("tags", "")).strip()),
                        steps=_split_multi(str(row.get("steps", "")).strip()),
                    )
                )
        return [c for c in cases if c.id and c.title]

    raise ValueError("Unsupported file type. Use .json or .csv")
