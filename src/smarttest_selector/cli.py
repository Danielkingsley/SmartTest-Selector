import argparse

from .loader import load_testcases
from .selector import SelectorEngine


def main() -> None:
    parser = argparse.ArgumentParser(description="SmartTest Selector")
    parser.add_argument("--input", required=True, help="Path to testcase file (.json/.csv)")
    parser.add_argument("--feature", required=True, help="Feature/change description")
    parser.add_argument("--top-k", type=int, default=10, help="Number of testcases to output")
    parser.add_argument("--min-score", type=float, default=0.05, help="Minimum relevance score")
    parser.add_argument(
        "--disable-llm-rerank",
        action="store_true",
        help="Skip OpenAI-compatible reranking",
    )
    args = parser.parse_args()

    testcases = load_testcases(args.input)
    engine = SelectorEngine(testcases)
    results = engine.select(
        feature_query=args.feature,
        top_k=args.top_k,
        min_score=args.min_score,
        use_llm_rerank=not args.disable_llm_rerank,
    )

    if not results:
        print("No relevant testcases found.")
        return

    print(f"Feature: {args.feature}\n")
    print("Selected Testcases:")
    for idx, result in enumerate(results, start=1):
        tc = result.testcase
        print(
            f"{idx}. [{tc.id}] {tc.title} | module={tc.module or '-'} | "
            f"score={result.score:.4f} | reason={result.reason}"
        )


if __name__ == "__main__":
    main()
