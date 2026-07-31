# Retailer-local item codes in Israeli supermarket receipts

## What the number means

Israeli supermarket price-transparency files identify each listed item with an
`ItemCode` and also publish product-description, quantity, unit-of-measure, and
weighted-item fields. In real chain files, `ItemCode` is not restricted to a
global barcode: loose produce and weighed department goods commonly use short
retailer-assigned numbers.

This is consistent with the wider produce system. IFPS PLUs are four or five
digits, while retailers are also free to maintain their own internal SKUs. A
short receipt code is therefore useful inside its retailer's catalogue but is
not a safe cross-chain join key.

Primary references:

- Israeli price-transparency source-file scraper and government regulation
  link: https://github.com/OpenIsraeliSupermarkets/israeli-supermarket-scarpers
- Parser and representative `ItemCode`-based files:
  https://github.com/OpenIsraeliSupermarkets/israeli-supermarket-parsers
- IFPS produce PLU definition: https://www.ifpsglobal.com/plu-codes

## What the deployed catalogue demonstrates

The price API accepts short codes at `/products/barcode/{code}`, but its product
index is global. That makes a bare short-code lookup unsafe:

- `9077667` describes `מלפפון/ירקות שקיל`.
- `935` describes `עגבניה 05`.
- `695` describes `תירס חסלט`, while a receipt from a different retailer can
  use `695` for cucumber.

The collision is the important case: exact numeric equality does not establish
product identity for a local code.

## Matching policy

1. A 12–14 digit code remains a global-barcode match with confidence `1.0`.
2. A shorter positive numeric code is classified as a retailer-local PLU/SKU.
3. The local code is queried directly, but the result is accepted only when its
   normalized product name also matches the receipt name.
4. Generic sale-mode words such as `שקיל`, `במשקל`, `ירקות`, and `תפזורת` are
   ignored only for this confirmation step.
5. A wider name search retrieves other short-code rows. Strong name-equivalent
   rows are retained as alternates.
6. Price comparison requests the primary and all retained equivalents. Each
   store can therefore price the code it actually publishes.
7. If direct-code text conflicts with the receipt, the numeric match is rejected
   and the line falls back to name matching.
8. If neither route reaches the confidence floor, the line remains unmatched.

The matcher reports `matched_by: "local_code"` separately from `"barcode"` and
`"name"` so callers can distinguish a globally certain identifier from a
name-confirmed retailer identifier.

## Current upstream limitation

The deployed API groups price rows by `productBarcode`, including short codes.
The ideal database key for a retailer-local item is `(chainId, ItemCode)`, with a
separate canonical-equivalence relation between chains. The client-side name
guard prevents known collisions from becoming exact matches and the alternate
codes enable useful comparisons, but a future backend migration to that
composite key would remove the remaining ambiguity at the source.
