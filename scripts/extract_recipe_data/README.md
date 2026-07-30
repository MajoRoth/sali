# Digital Receipt URL extractor POC

This proof of concept extracts one public Digital Receipt URL into a strict,
platform-neutral JSON Receipt Document. It first asks GPT-5.6 Luna to inspect
the exact URL through OpenAI-hosted web search. If hosted retrieval cannot read
the page, a generic isolated Playwright browser renders it and a second
structured OpenAI request extracts the captured text and screenshot.

The fallback is merchant-agnostic: it does not contain platform host checks,
merchant selectors, private API paths, or receipt-specific parsers.

## Install

The project requires Python 3.13 or newer:

```bash
uv sync
uv run playwright install chromium
```

Set `OPENAI_API_KEY` in the shell or in the repository root `.env`:

```bash
export OPENAI_API_KEY='<your-project-api-key>'
```

The `.env` file is git-ignored and should remain private.

## Run

From the repository root:

```bash
uv run python scripts/extract_recipe_data/extract_receipt_via_openai.py \
  'https://merchant.example/receipt/private-token'
```

The script:

- accepts one public HTTPS URL;
- first sends it to `gpt-5.6-luna` using OpenAI-hosted web search restricted to
  the supplied hostname;
- falls back only for hosted `unreachable`, `blocked`, or
  `insufficient_evidence` results;
- renders fallback pages in a fresh headless-browser context;
- sends bounded visible text and an optional screenshot to a second structured
  OpenAI request with `store=False`;
- verifies that the page is evidence of a completed purchase;
- parses a strict Structured Output;
- reconciles item and receipt totals locally using decimal arithmetic;
- writes `output/hosted_receipt.json` with private `0600` permissions.

It refuses to overwrite existing output unless `--force` is supplied. If the
page is inaccessible, is not a receipt, lacks sufficient evidence, or fails
local reconciliation, the command exits unsuccessfully and writes no JSON.
Hosted-verification failures include the model's evidence-based
`failure_reason` and the status/action of each web-search call, so a model
classification such as `unreachable` is not confused with an API failure.

## Design

The executable is a compatibility entry point that composes focused classes:

- `ApiKeyProvider` loads credentials;
- `ReceiptUrlValidator` enforces and normalizes public HTTPS URLs;
- `HostedReceiptExtractor` performs structured extraction and reconciliation;
- `AutoReceiptExtractor` selects hosted or rendered evidence;
- `BrowserReceiptRenderer` captures generic rendered evidence;
- `RenderedEvidenceReceiptExtractor` performs multimodal structured extraction;
- `PublicNetworkPolicy` blocks private, local, and insecure browser requests;
- `OpenAIReceiptExtractor` owns the OpenAI client and fallback lifecycle;
- `ReceiptDocumentWriter` writes private JSON atomically;
- `ReceiptExtractionApplication` coordinates the command-line workflow.

Configuration, domain errors, extraction models, and receipt models live in
separate modules so each responsibility can be tested independently.

## Receipt Document

The saved UTF-8 JSON is the same shape intended for the future HTTP API:

```json
{
  "schema_version": "1.0",
  "receipt": {
    "merchant": {
      "name": "Example Market",
      "branch_name": null,
      "branch_number": null
    },
    "transaction": {
      "receipt_id": null,
      "purchased_at": "2026-07-30T18:42:00+03:00",
      "transaction_number": "42",
      "type": "purchase",
      "currency": "ILS"
    },
    "totals": {
      "subtotal": "12.90",
      "discounts": "0",
      "total": "12.90"
    },
    "items": [
      {
        "position": 1,
        "code": "000123",
        "name": "Example product",
        "categories": [],
        "quantity": "1",
        "unit": "item",
        "unit_price": "12.90",
        "gross_total": "12.90",
        "adjustments": [],
        "final_total": "12.90"
      }
    ]
  },
  "warnings": []
}
```

Money and fractional quantities are decimal strings to avoid floating-point
precision loss. Unknown optional fields remain `null`; collections remain
arrays. Source URLs, browsing citations, customer identity, contact details,
and payment information are excluded from saved output.

## Validate

Tests use synthetic receipt data and a mocked OpenAI client:

```bash
uv run pytest tests/extract_recipe_data
uv run ruff check scripts/extract_recipe_data tests/extract_recipe_data
```

Optional live verification requires `OPENAI_API_KEY` and incurs API usage:

```bash
uv run python scripts/extract_recipe_data/extract_receipt_via_openai.py \
  --force 'https://merchant.example/receipt/private-token'
```

## Limitations

- Only unauthenticated public HTTPS URLs are accepted.
- Authenticated, expired, CAPTCHA-protected, or interaction-gated receipts may
  still be unavailable.
- The browser fallback allows only public HTTPS destinations and keeps
  top-level navigation on the supplied hostname. Receipts requiring a
  cross-host redirect fail closed.
- Extraction is probabilistic; local reconciliation fails closed instead of
  returning price data whose arithmetic cannot be trusted.
