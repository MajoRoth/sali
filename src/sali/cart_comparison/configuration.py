"""Configuration for talking to the Open Supermarkets price database."""

from __future__ import annotations

import os

#: Base URL of the Open Supermarkets API. Overridable so a local or staging
#: instance can be pointed at without editing code.
DEFAULT_CATALOG_URL = "http://34.165.235.189:8000"

#: `/products/compare-prices` rejects more than 20 ids per call, so a cart is
#: always split into batches of this size.
MAX_PRODUCT_IDS_PER_REQUEST = 20

#: Candidates fetched per name search. The endpoint is a substring match over
#: product names, so a short receipt word can return thousands of rows; only the
#: first page is ever scored.
SEARCH_CANDIDATE_LIMIT = 25

#: Minimum name-match score for a fallback match to be accepted. Below this the
#: line is reported unmatched rather than priced against the wrong product,
#: because a wrong match silently corrupts a store's cart total.
MIN_NAME_MATCH_SCORE = 0.5

#: Score at or above which a name match needs no second look. Between this and
#: the floor the product is priced but reported as uncertain: `תפו"א לבן`
#: matching `תפוא אדום` is the shape of error only a human can see.
CONFIDENT_NAME_MATCH_SCORE = 0.8

#: A receipt code is treated as a barcode only at these lengths. Shorter codes
#: on Israeli receipts are merchant-internal PLUs for weighed goods, which the
#: catalogue does not key on.
BARCODE_LENGTHS = frozenset({12, 13, 14})

CATALOG_TIMEOUT_SECONDS = 30.0


def catalog_base_url() -> str:
    """The price database this service compares carts against."""
    return os.environ.get("SALI_PRICES_API_URL", DEFAULT_CATALOG_URL).rstrip("/")
