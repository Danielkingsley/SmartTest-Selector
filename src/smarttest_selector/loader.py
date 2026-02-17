import base64
import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
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
        result: List[str] = []
        for item in value:
            if isinstance(item, dict):
                name = item.get("name") or item.get("label") or item.get("value") or item.get("title")
                if name:
                    result.append(str(name).strip())
            else:
                clean = str(item).strip()
                if clean:
                    result.append(clean)
        return result
    if isinstance(value, str):
        if "|" in value:
            return _split_multi(value)
        if "," in value:
            return [item.strip() for item in value.split(",") if item.strip()]
        return [value.strip()] if value.strip() else []
    return [str(value).strip()]


def _extract_testcase_payload(item: Dict[str, Any]) -> Dict[str, Any]:
    nested = item.get("test_case")
    if isinstance(nested, dict):
        merged = dict(item)
        merged.update(nested)
        return merged
    return item


def _from_record(item: Dict[str, object]) -> Optional[TestCase]:
    payload = _extract_testcase_payload(item)
    testcase_id = str(
        payload.get("id")
        or payload.get("identifier")
        or payload.get("key")
        or payload.get("testcase_id")
        or payload.get("test_case_id")
        or ""
    ).strip()
    title = str(payload.get("title") or payload.get("name") or payload.get("test_case_name") or "").strip()
    if not testcase_id or not title:
        return None

    description = str(
        payload.get("description")
        or payload.get("objective")
        or payload.get("precondition")
        or payload.get("preconditions")
        or ""
    ).strip()

    tags = _to_list(payload.get("tags") or payload.get("labels") or payload.get("custom_tags"))
    steps = _to_list(payload.get("steps") or payload.get("test_steps") or payload.get("scenario"))

    return TestCase(
        id=testcase_id,
        title=title,
        description=description,
        module=str(payload.get("module") or payload.get("component") or payload.get("suite") or "").strip(),
        tags=tags,
        steps=steps,
    )


def load_testcases(path: str) -> List[TestCase]:
    input_path = Path(path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    if input_path.suffix.lower() == ".json":
        with input_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        parsed = [_from_record(item) for item in data if isinstance(item, dict)]
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


def _extract_records(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    for key in ("test_cases", "testcases", "data", "items", "results"):
        records = payload.get(key)
        if isinstance(records, list):
            return [row for row in records if isinstance(row, dict)]
    return []


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

        if not isinstance(payload, dict):
            raise ValueError("Unexpected BrowserStack API response: expected JSON object")

        records = _extract_records(payload)
        parsed = [_from_record(item) for item in records]
        testcases.extend(case for case in parsed if case)

        has_next = bool(payload.get("next") or payload.get("has_next") or payload.get("next_page") or payload.get("nextPage"))
        if not records or not has_next:
            break
        page += 1

    return testcases
