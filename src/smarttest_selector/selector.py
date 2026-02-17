import json
import math
import os
import re
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from .models import TestCase


TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")


def tokenize(text: str) -> List[str]:
    return TOKEN_RE.findall(text.lower())


def cosine_similarity(a: Dict[str, float], b: Dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(a.get(term, 0.0) * b.get(term, 0.0) for term in set(a) & set(b))
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if not norm_a or not norm_b:
        return 0.0
    return dot / (norm_a * norm_b)


def tf_vector(text: str) -> Dict[str, float]:
    tokens = tokenize(text)
    counts = Counter(tokens)
    if not counts:
        return {}
    length = float(sum(counts.values()))
    return {token: count / length for token, count in counts.items()}


@dataclass
class SelectionResult:
    testcase: TestCase
    score: float
    reason: str


class SelectorEngine:
    def __init__(self, testcases: Sequence[TestCase]):
        self.testcases = list(testcases)
        self.case_vectors = {case.id: tf_vector(case.searchable_text()) for case in self.testcases}

    def select(
        self,
        feature_query: str,
        top_k: int = 10,
        min_score: float = 0.05,
        use_llm_rerank: bool = True,
    ) -> List[SelectionResult]:
        query_vector = tf_vector(feature_query)
        scored: List[Tuple[TestCase, float]] = []

        for case in self.testcases:
            score = cosine_similarity(query_vector, self.case_vectors[case.id])
            if score >= min_score:
                scored.append((case, score))

        if not scored and self.testcases:
            fallback_scored = [
                (case, cosine_similarity(query_vector, self.case_vectors[case.id]))
                for case in self.testcases
            ]
            fallback_scored.sort(key=lambda item: item[1], reverse=True)
            return [
                SelectionResult(testcase=case, score=score, reason="Fallback: low lexical overlap")
                for case, score in fallback_scored[:top_k]
            ]

        scored.sort(key=lambda item: item[1], reverse=True)
        candidates = scored[: max(top_k * 3, top_k)]

        results = [
            SelectionResult(testcase=case, score=score, reason="Semantic lexical similarity")
            for case, score in candidates
        ]

        if use_llm_rerank:
            reranked = self._llm_rerank(feature_query, results, top_k)
            if reranked:
                return reranked

        return results[:top_k]

    def _llm_rerank(
        self,
        feature_query: str,
        candidates: List[SelectionResult],
        top_k: int,
    ) -> List[SelectionResult]:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or not candidates:
            return []

        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        endpoint = os.getenv("OPENAI_ENDPOINT", "https://api.openai.com/v1/chat/completions")

        payload = {
            "model": model,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a QA test selector. Return only JSON.",
                },
                {
                    "role": "user",
                    "content": (
                        "Feature: "
                        + feature_query
                        + "\nCandidates:\n"
                        + json.dumps(
                            [
                                {
                                    "id": c.testcase.id,
                                    "title": c.testcase.title,
                                    "description": c.testcase.description,
                                    "module": c.testcase.module,
                                    "tags": c.testcase.tags,
                                }
                                for c in candidates
                            ]
                        )
                        + "\nReturn JSON as {\"selected\": [{\"id\": string, \"reason\": string, \"score\": number}]}"
                    ),
                },
            ],
            "response_format": {"type": "json_object"},
        }

        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError):
            return []

        try:
            content = body["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            selected = parsed.get("selected", [])
        except (KeyError, IndexError, json.JSONDecodeError, TypeError):
            return []

        score_map = {item["id"]: item for item in selected if "id" in item}
        candidate_map = {c.testcase.id: c for c in candidates}

        reranked: List[SelectionResult] = []
        for item in selected:
            candidate = candidate_map.get(item.get("id"))
            if not candidate:
                continue
            llm_score = float(item.get("score", candidate.score))
            reranked.append(
                SelectionResult(
                    testcase=candidate.testcase,
                    score=llm_score,
                    reason=item.get("reason", "LLM reranked"),
                )
            )

        if not reranked:
            return []

        reranked.sort(key=lambda r: r.score, reverse=True)
        return reranked[:top_k]
