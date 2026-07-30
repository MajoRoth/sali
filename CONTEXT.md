# Receipt Intelligence

This context describes purchase evidence and the normalized commercial facts
extracted from it for price analysis.

## Language

**Digital Receipt**:
A merchant-issued proof of purchase accessible through a URL, containing
transaction metadata and purchased line items.
_Avoid_: Digital recipe, recipe

**Verified Digital Receipt**:
A Digital Receipt whose accessible evidence establishes that it is
merchant-issued purchase evidence and supports extraction of its transaction,
total, and line-item facts.
_Avoid_: Plausible receipt page, assumed receipt

**Normalized Receipt**:
A platform-independent, schema-validated representation of a Digital Receipt's
merchant, transaction totals, and ordered line items.
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
