"""Configuration for talking to the Open Supermarkets price database.

One deployment now serves both halves of the question: the Cloud Run backend
publishes prices (`compare-prices` with per-store breakdowns), store
coordinates, and chain listings, all without a token. The price and geocoding
URLs are still configured separately because the code that joins them — see
`sali.nearby.stores` — was built for the era when they were two hosts with
disjoint data, and keeping the seam costs nothing while allowing either side
to be swapped out again.

Measured against real receipts (July 2026): 14 of its 58 chains publish
prices. The rest — שופרסל, רמי לוי, קרפור, אושר עד among them — have branches
and coordinates but no listings, which is the ceiling on how many stores any
cart can be priced at.
"""

from __future__ import annotations

import os

#: The instance that publishes prices.
DEFAULT_CATALOG_URL = "https://sali-backend-api-930679045173.me-west1.run.app"

#: The instance store coordinates are read from. Currently the same deployment
#: as the prices; kept separate so map pins can outlive a pricing outage.
DEFAULT_GEOCODING_URL = "https://sali-backend-api-930679045173.me-west1.run.app"

#: Shipped so the app runs out of the box against the public dataset. Anyone
#: needing their own quota sets `SUPERMARKET_API_KEY`.
DEFAULT_CATALOG_TOKEN = "001d35a9-09fb-4805-8fe2-c86f69bc03ce"

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

#: Floor for pricing a line by name when its *printed barcode* is not in the
#: catalogue. Higher than the weighed-goods floor on purpose: a PLU line has no
#: other route, but a barcode line names an exact product, so a name is only
#: trusted here when it is nearly beyond doubt — the store-brand פתי בר whose
#: barcode the database lacks, not a loose lookalike.
BARCODE_MISS_NAME_SCORE = 0.75

#: How many equally-valid readings ride along with a name match. Each one costs
#: a slot in the `compare-prices` batches, and past a few the extras are the
#: same generic produce name repeated across chains.
ALTERNATE_MATCH_LIMIT = 4

#: A receipt code is treated as a barcode only at these lengths. Shorter codes
#: on Israeli receipts are merchant-internal PLUs for weighed goods, which the
#: catalogue does not key on.
BARCODE_LENGTHS = frozenset({12, 13, 14})

#: A healthy barcode lookup takes about five seconds and a search about ten, so
#: this is generous for a working host — and it is the unit in which a shopper
#: waits on a broken one, which is why it is not more generous than that.
CATALOG_TIMEOUT_SECONDS = 15.0

#: `/products/search` gets a shorter leash than the rest. It is the optional
#: half of matching — a line it cannot resolve is reported unmatched, not
#: failed — and it is also the endpoint that hangs, so waiting the full budget
#: on it buys nothing and costs the shopper the whole request.
SEARCH_TIMEOUT_SECONDS = 8.0

#: How many times a call is attempted before giving up. The hosted service
#: answers a barcode lookup in about five seconds and occasionally 504s under
#: that load, so one retry converts most failures into answers; more than that
#: and the shopper is waiting on a service that is plainly having a bad minute.
CATALOG_RETRY_ATTEMPTS = 2

CATALOG_RETRY_BACKOFF_SECONDS = 0.4

#: Concurrent barcode lookups. The hosted catalogue has no bulk endpoint and
#: takes a second or two per barcode, so a fifty-line receipt resolved serially
#: takes minutes. Measured over a warm connection pool, eighteen lookups take
#: 8.5s at 2 workers and 4.7s at 8; past that the curve is flat, so this is the
#: point where more concurrency stops buying anything and only adds load.
BARCODE_LOOKUP_WORKERS = 8

#: Sockets kept open to each host. What actually makes the hosted service
#: usable: the same request volume that succeeds over a warm pool gets refused
#: when every call opens its own connection.
CONNECTION_POOL_SIZE = 16

#: Long enough that the pool survives between the phases of one request —
#: matching, then pricing, then swap search.
KEEPALIVE_EXPIRY_SECONDS = 60.0

#: How many receipt lines are searched for a cheaper alternative. Each search is
#: a slow catalogue call, and swaps only pay off on the expensive lines, so the
#: cart's priciest lines are searched and the long tail of cheap ones is not.
SWAP_SEARCH_LINES = 12

#: Concurrent swap searches. Lower than the barcode cap because search is the
#: slower endpoint of the two and this work is an optional improvement.
SWAP_SEARCH_WORKERS = 8

#: Consecutive failures after which a host is treated as down and calls are
#: skipped. A fifty-line receipt against a dead service would otherwise be
#: fifty lookups times two attempts times a thirty-second timeout.
CIRCUIT_BREAKER_THRESHOLD = 4

#: How long calls are skipped before one is let through to test the water.
CIRCUIT_BREAKER_COOLDOWN_SECONDS = 60.0


def catalog_base_url() -> str:
    """The price database this service compares carts against."""
    return os.environ.get("SALI_PRICES_API_URL", DEFAULT_CATALOG_URL).rstrip("/")


def geocoding_base_url() -> str:
    """The instance store coordinates are read from."""
    return os.environ.get("SALI_GEOCODING_API_URL", DEFAULT_GEOCODING_URL).rstrip("/")


def catalog_token() -> str | None:
    """The bearer token for the price database, if one is needed."""
    token = os.environ.get("SUPERMARKET_API_KEY", DEFAULT_CATALOG_TOKEN).strip()
    return token or None


def catalog_headers() -> dict[str, str]:
    """Auth headers for the price database.

    The hosted service rejects a bare token with `Invalid token format`; it
    wants the `Bearer` scheme. The open instance ignores the header entirely,
    so sending it always is safe and keeps one code path.
    """
    token = catalog_token()
    return {"Authorization": f"Bearer {token}"} if token else {}
