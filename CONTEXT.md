# Receipt Intelligence

This context describes purchase evidence and the normalized commercial facts
extracted from it for price analysis.

## Language

**Digital Receipt**:
A merchant-issued proof of purchase accessible through a URL, containing
transaction metadata and purchased line items.
_Avoid_: Digital recipe, recipe

**Receipt Evidence**:
The sanitized merchant, transaction, product, and total information derived
from a Digital Receipt and permitted to leave the local capture boundary.
_Avoid_: Raw HTML, full page source
