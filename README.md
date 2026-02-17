# SmartTest Selector

SmartTest Selector is an **LLM-assisted test case selector** for BrowserStack (or any regression suite export).

Given a feature/change description such as:

- `PLP page filters`
- `checkout payment retry`
- `product details image zoom`

it ranks and returns only the most relevant test cases from your master test suite.

## How it works

1. Load test cases from JSON/CSV or directly from BrowserStack Test Management API.
2. Build a semantic index using a local embedding model (token-vector cosine).
3. Optionally re-rank with an OpenAI-compatible LLM if `OPENAI_API_KEY` is set.
4. Output top matching tests with relevance scores and rationale.

## Project structure

- `src/smarttest_selector/models.py` – data model for test cases
- `src/smarttest_selector/selector.py` – semantic retrieval and optional LLM reranking
- `src/smarttest_selector/loader.py` – CSV/JSON ingestion helpers
- `src/smarttest_selector/cli.py` – command-line interface
- `tests/` – unit tests

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src python -m smarttest_selector.cli \
  --input data/sample_testcases.json \
  --feature "PLP page sorting and filters" \
  --top-k 5
```

## Input format

### JSON

```json
[
  {
    "id": "TC-101",
    "title": "PLP - Filter by brand",
    "description": "Validate shoppers can filter product list by selected brand",
    "tags": ["plp", "filter", "catalog"],
    "module": "PLP",
    "steps": ["Open PLP", "Apply brand filter", "Verify products are filtered"]
  }
]
```

### CSV columns

Required: `id`, `title`

Optional: `description`, `module`, `tags`, `steps`

- `tags` and `steps` can be pipe-separated (`|`) values.


### BrowserStack API

You can pull testcases directly using project id + credentials:

```bash
PYTHONPATH=src python -m smarttest_selector.cli \
  --browserstack-project-id "<project_id>" \
  --browserstack-username "$BROWSERSTACK_USERNAME" \
  --browserstack-access-key "$BROWSERSTACK_ACCESS_KEY" \
  --feature "PLP page filters" \
  --top-k 10 \
  --show-source-count
```

Optional: if your account uses a different endpoint path, pass `--browserstack-endpoint-template`.

## LLM re-ranking (optional)

Set environment variables:

- `OPENAI_API_KEY`
- `OPENAI_MODEL` (default: `gpt-4o-mini`)

When enabled, the app first retrieves semantic candidates and then asks the model to re-rank for precision.

## Example

Feature input: `PLP page`

Expected output: test cases around product list page filters, sort, pagination, and card rendering — while excluding checkout/login cases.


Notes:
- For `--browserstack-username`, use your BrowserStack account username/email only (for example `name@example.com`).
- Do **not** pass URL style values such as `http://username@browserstack.com`.
- If you still get no matches, try lowering threshold explicitly with `--min-score 0`.
