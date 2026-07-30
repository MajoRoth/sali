# Weezmo receipt extractor POC

This proof of concept turns one or more Weezmo digital-receipt links into a
single, normalized CSV of purchased products.

Although the original folder name says `recipe`, the supplied links are
receipts. The code therefore uses receipt terminology.

## How it works

The visible receipt page is a React shell. Different merchants render their
items with different HTML, but the current Weezmo frontend first requests the
same structured JSON endpoint for both:

```text
GET https://receipts.weezmo.com/api/receipts/{receipt UUID}?withTemplate=false
```

The extractor reads the `q` receipt UUID from each supplied URL, requests that
compact JSON, validates that the returned receipt and optional `b` business UUID
match the URL, and whitelists product and basic receipt fields into the CSV. It
does not export payment data or the raw receipt payload.

## Run

From the repository root:

```bash
uv run python scripts/extract_recipe_data/extract_receipts.py \
  'https://receipts.weezmo.com/cms.html?q=<receipt-uuid>&b=<business-uuid>&cookie=true' \
  --output scripts/extract_recipe_data/weezmo_receipts.csv
```

You can pass multiple URLs, or pass a bare receipt UUID. Duplicate receipts are
fetched only once. The default output is
`scripts/extract_recipe_data/weezmo_receipts.csv`.

The CSV is UTF-8 with a byte-order mark so Hebrew text opens correctly in Excel.
It contains receipt and merchant identifiers, branch and purchase metadata,
product code/name, unit price, quantity, gross line total, item adjustments, and
a calculated net line total. Product codes remain text, including leading
zeroes. Text beginning with a spreadsheet formula prefix is escaped. Generated
CSVs in this folder are git-ignored because a live receipt ID currently grants
access to the underlying receipt data.

## Validate

```bash
uv run pytest scripts/extract_recipe_data
uv run ruff check scripts/extract_recipe_data
```

The tests also use only the Python standard library:

```bash
python3 -m unittest scripts.extract_recipe_data.test_extract_receipts
```

## POC limitations

- The endpoint is an undocumented implementation detail of Weezmo's current
  frontend and may change.
- Anyone with a receipt UUID can currently query that receipt. Treat receipt
  links, IDs, and generated CSVs as private data.
- The endpoint is rate-limited. This CLI de-duplicates inputs and reports HTTP
  429 without retrying; it is intended for low-volume use.
- The tool only supports receipts with structured `items`. It does not yet
  perform OCR when Weezmo provides only an image or original receipt text.
- Some merchants put promotions in `item.additionalData` rather than the normal
  discount fields. The POC preserves those entries as JSON. It considers only
  negative numeric values to be candidate adjustments and applies them only
  when the resulting sum reconciles to the receipt total; otherwise they remain
  visible but unapplied.
- Purchase timestamps are preserved exactly as Weezmo returns them because
  timezone handling is inconsistent across merchants.
