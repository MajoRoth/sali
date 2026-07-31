# Receipt Intelligence

This context describes purchase evidence and the normalized commercial facts
extracted from it for price analysis.

## Language

**Digital Receipt**:
A merchant-issued proof of purchase accessible through a URL, containing
transaction metadata and purchased line items.
_Avoid_: Digital recipe, recipe

**Receipt Image**:
A user-supplied photograph or scan of a completed purchase receipt, containing
visual purchase evidence rather than a merchant-hosted URL.
_Avoid_: Digital Receipt, receipt upload

**Verified Receipt Image**:
A Receipt Image whose readable visual evidence supports extraction of its
transaction, total, and line-item facts.
_Avoid_: Plausible receipt photo, assumed receipt

**Receipt Image Total**:
The final paid amount and currency read from a Receipt Image when the image
supports the total but not a complete set of purchasable line items.
_Avoid_: Reconciled Receipt, complete cart

**Verified Digital Receipt**:
A Digital Receipt whose accessible evidence establishes that it is
merchant-issued purchase evidence and supports extraction of its transaction,
total, and line-item facts.
_Avoid_: Plausible receipt page, assumed receipt

**Normalized Receipt**:
A platform-independent, schema-validated representation of a Digital Receipt
or Verified Receipt Image's merchant, transaction totals, and ordered line
items.
_Avoid_: Model-generated CSV, unvalidated model output

**Reconciled Receipt**:
A Normalized Receipt whose line totals and applied adjustments match its stated
receipt total within the configured currency tolerance.
_Avoid_: Plausible receipt, unchecked extraction

**Receipt Document**:
The versioned, API-ready JSON representation of a Reconciled Receipt, written
by the POC only beneath its dedicated git-ignored local output directory and
intended to become a future API response body.
_Avoid_: CSV export, model response

**Receipt Image Total Document**:
An API response that represents a Receipt Image Total and explicitly warns that
it does not contain a complete cart.
_Avoid_: Receipt Document, normalized receipt

**Receipt Evidence**:
The sanitized merchant, transaction, product, and total information derived
from a Digital Receipt and permitted to leave the local capture boundary.
_Avoid_: Raw HTML, full page source

## API Client Regeneration

The API client is auto-generated using openapi-python-client. It lives in src/supermarket-api-client. If the backend API changes, you must first extract the latest OpenAPI specification and then regenerate the client package.

From the root of the project, run:

```bash
# 1. Extract the latest OpenAPI specification from the FastAPI backend
cd supermarket_api_backend
uv run dump_openapi.py
cd ..

# 2. Regenerate the Python client
uvx openapi-python-client generate --path openapi/supermarkets_openapi.json --meta uv --output-path src/supermarket-api-client --overwrite
```

