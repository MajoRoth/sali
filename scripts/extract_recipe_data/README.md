# Digital Receipt URL extractor POC

This proof of concept sends one public Digital Receipt URL to GPT-5.6 Luna
through the OpenAI Responses API. OpenAI-hosted web search verifies the page and
extracts a strict, platform-neutral JSON Receipt Document.

The URL is the only receipt input sent by the script. There is no local HTML
fetching, browser rendering, platform adapter, or fallback parser.

## Install

The project requires Python 3.13 or newer:

```bash
uv sync
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
- sends it to `gpt-5.6-luna`;
- requires OpenAI-hosted web search restricted to the supplied hostname;
- makes exactly one OpenAI request with `store=False`;
- verifies that the page is evidence of a completed purchase;
- parses a strict Structured Output;
- reconciles item and receipt totals locally using decimal arithmetic;
- writes `output/hosted_receipt.json` with private `0600` permissions.

It refuses to overwrite existing output unless `--force` is supplied. If the
page is inaccessible, is not a receipt, lacks sufficient evidence, or fails
local reconciliation, the command exits unsuccessfully and writes no JSON.

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
uv run pytest scripts/extract_recipe_data
uv run ruff check scripts/extract_recipe_data
```

## Limitations

- Only unauthenticated public HTTPS URLs are accepted.
- OpenAI-hosted browsing may not read JavaScript-heavy, expired, tokenized, or
  cookie-gated receipt URLs.
- Extraction is probabilistic; local reconciliation fails closed instead of
  returning price data whose arithmetic cannot be trusted.
