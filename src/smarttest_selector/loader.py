import base64
import csv
import json
from pathlib import Path
from typing import Dict, List, Optional
import urllib.parse
import urllib.request

from .models import TestCase


def _split_multi(value: str) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split("|") if item.strip()]


def _to_list(value: object) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        if "|" in value:
            return _split_multi(value)
        if "," in value:
            return [item.strip() for item in value.split(",") if item.strip()]
        return [value.strip()] if value.strip() else []
    return [str(value).strip()]


def _from_record(item: Dict[str, object]) -> Optional[TestCase]:
    testcase_id = str(item.get("id") or item.get("testcase_id") or item.get("test_case_id") or "").strip()
    title = str(item.get("title") or item.get("name") or "").strip()
    if not testcase_id or not title:
        return None

    return TestCase(
        id=testcase_id,
        title=title,
        description=str(item.get("description") or item.get("objective") or "").strip(),
        module=str(item.get("module") or item.get("component") or item.get("suite") or "").strip(),
        tags=_to_list(item.get("tags")),
        steps=_to_list(item.get("steps") or item.get("test_steps")),
    )


def load_testcases(path: str) -> List[TestCase]:
    input_path = Path(path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    if input_path.suffix.lower() == ".json":
        with input_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        parsed = [_from_record(item) for item in data]
        return [case for case in parsed if case]

    if input_path.suffix.lower() == ".csv":
        cases: List[TestCase] = []
        with input_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                case = _from_record(dict(row))
                if case:
                    cases.append(case)
        return cases

    raise ValueError("Unsupported file type. Use .json or .csv")


def load_testcases_from_browserstack(
    project_id: str,
    username: str,
    access_key: str,
    endpoint_template: str = "https://test-management.browserstack.com/api/v2/projects/{project_id}/test-cases",
) -> List[TestCase]:
    if not project_id:
        raise ValueError("project_id is required")

    auth = base64.b64encode(f"{username}:{access_key}".encode("utf-8")).decode("utf-8")
    base_url = endpoint_template.format(project_id=urllib.parse.quote(project_id, safe=""))

    testcases: List[TestCase] = []
    page = 1

    while True:
        page_url = f"{base_url}?page={page}"
        request = urllib.request.Request(
            page_url,
            headers={
                "Authorization": f"Basic {auth}",
                "Accept": "application/json",
            },
            method="GET",
        )

        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))

        records = payload.get("test_cases") or payload.get("testcases") or payload.get("data") or []
        if not isinstance(records, list):
            raise ValueError("Unexpected BrowserStack API response: expected list of test cases")

        parsed = [_from_record(item) for item in records if isinstance(item, dict)]
        testcases.extend(case for case in parsed if case)

        has_next = bool(payload.get("next") or payload.get("has_next") or payload.get("next_page"))
        if not records or not has_next:
            break
        page += 1

    return testcases
