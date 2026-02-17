import argparse

from .loader import load_testcases, load_testcases_from_browserstack
from .selector import SelectorEngine


def main() -> None:
    parser = argparse.ArgumentParser(description="SmartTest Selector")
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--input", help="Path to testcase file (.json/.csv)")
    source_group.add_argument("--browserstack-project-id", help="BrowserStack test management project id")

    parser.add_argument("--feature", required=True, help="Feature/change description")
    parser.add_argument("--top-k", type=int, default=10, help="Number of testcases to output")
    parser.add_argument("--min-score", type=float, default=0.05, help="Minimum relevance score")
    parser.add_argument(
        "--disable-llm-rerank",
        action="store_true",
        help="Skip OpenAI-compatible reranking",
    )

    parser.add_argument("--browserstack-username", help="BrowserStack username/email")
    parser.add_argument("--browserstack-access-key", help="BrowserStack access key")
    parser.add_argument(
        "--browserstack-endpoint-template",
        default="https://test-management.browserstack.com/api/v2/projects/{project_id}/test-cases",
        help="Override BrowserStack API endpoint template",
    )
    parser.add_argument(
        "--show-source-count",
        action="store_true",
        help="Print number of loaded testcases before selection",
    )
    args = parser.parse_args()

    if args.input:
        testcases = load_testcases(args.input)
    else:
        if not args.browserstack_username or not args.browserstack_access_key:
            parser.error("--browserstack-username and --browserstack-access-key are required with --browserstack-project-id")
        testcases = load_testcases_from_browserstack(
            project_id=args.browserstack_project_id,
            username=args.browserstack_username,
            access_key=args.browserstack_access_key,
            endpoint_template=args.browserstack_endpoint_template,
        )

    if args.show_source_count:
        print(f"Loaded testcases: {len(testcases)}")

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
