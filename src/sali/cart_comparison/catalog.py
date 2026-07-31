"""Client for the Open Supermarkets price database.

The endpoints this talks to are read-only, so the client's whole job is shape:
batching `compare-prices` under its 20-id ceiling, turning a 404 into "no such
product" rather than an exception, and never letting one slow upstream call
fail a whole cart.

Speed is the other half of the job, and it is mostly about connections. The
hosted service answers a barcode in a second or two over a warm pool and
refuses the same volume when every call opens its own socket — so one pooled
client is reused for the life of the object, lookups run concurrently over it,
and their results are cached.
"""

from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Self

import httpx

from sali.cart_comparison.configuration import (
    BARCODE_LOOKUP_WORKERS,
    CATALOG_RETRY_ATTEMPTS,
    CATALOG_RETRY_BACKOFF_SECONDS,
    CATALOG_TIMEOUT_SECONDS,
    CIRCUIT_BREAKER_COOLDOWN_SECONDS,
    CIRCUIT_BREAKER_THRESHOLD,
    CONNECTION_POOL_SIZE,
    KEEPALIVE_EXPIRY_SECONDS,
    MAX_PRODUCT_IDS_PER_REQUEST,
    SEARCH_CANDIDATE_LIMIT,
    SEARCH_TIMEOUT_SECONDS,
    catalog_base_url,
    catalog_headers,
)

logger = logging.getLogger(__name__)

#: Distinguishes "cached as absent" from "never looked up".
_MISSING = object()

#: Returned by `_get` when a failure was tolerated. Distinct from None, which
#: means the host answered and said the resource does not exist — caching those
#: two as the same thing would let one outage mark a product permanently absent.
_FAILED = object()


def _timeout_for(path: str) -> float:
    """How long this endpoint is worth waiting for."""
    return SEARCH_TIMEOUT_SECONDS if path.startswith("/products/search") else CATALOG_TIMEOUT_SECONDS


def _circuit_key(path: str) -> str:
    """Which endpoint a path belongs to, ignoring the id on the end.

    `/products/barcode/729...` and `/products/barcode/838...` are one endpoint
    and share a health story; `/products/search` is a different one entirely.
    """
    parts = [part for part in path.split("/") if part][:2]
    return "/" + "/".join(parts)


class CatalogUnavailableError(RuntimeError):
    """The price database could not be reached or answered unusably."""


@dataclass(frozen=True)
class ProductLookup:
    """What a barcode lookup found, and whether it got an answer at all.

    The distinction is the whole point. "The database has no such product" and
    "the database did not respond" both leave us without a product, but only
    the first is a fact about the shopper's receipt — and telling them their
    milk is not in the database when really the server was down is a plain
    falsehood.
    """

    product: dict[str, Any] | None
    answered: bool


class SupermarketsCatalog:
    """Read products, prices, and stores from the Open Supermarkets API."""

    def __init__(
        self,
        base_url: str | None = None,
        client: httpx.Client | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._base_url = (base_url or catalog_base_url()).rstrip("/")
        self._client = client
        self._headers = catalog_headers() if headers is None else headers
        self._owned: httpx.Client | None = None
        self._products: dict[str, dict[str, Any] | None] = {}
        self._lock = threading.RLock()
        self._failures: dict[str, int] = {}
        self._opened_at: dict[str, float] = {}

    def _session(self) -> httpx.Client:
        """The pooled client every request goes through.

        Built once and kept. Opening a fresh client per request means a new TCP
        and TLS handshake per product, and a fifty-line receipt then arrives as
        fifty simultaneous new connections — which the hosted service refuses,
        while the identical request volume over a warm pool succeeds. Measured:
        eighteen barcode lookups over one pooled client finish in under five
        seconds with no failures; the same lookups on per-request clients trip
        the circuit breaker after four.
        """
        if self._client is not None:
            return self._client
        with self._lock:
            if self._owned is None:
                self._owned = httpx.Client(
                    timeout=CATALOG_TIMEOUT_SECONDS,
                    headers=self._headers,
                    limits=httpx.Limits(
                        max_connections=CONNECTION_POOL_SIZE,
                        max_keepalive_connections=CONNECTION_POOL_SIZE,
                        keepalive_expiry=KEEPALIVE_EXPIRY_SECONDS,
                    ),
                )
            return self._owned

    def _request(
        self,
        path: str,
        params: Any | None = None,
    ) -> httpx.Response:
        return self._session().get(
            f"{self._base_url}{path}",
            params=params,
            headers=self._headers,
            timeout=_timeout_for(path),
        )

    def close(self) -> None:
        """Release the pooled connections. Injected clients are the caller's."""
        with self._lock:
            owned, self._owned = self._owned, None
        if owned is not None:
            owned.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def _get(
        self,
        path: str,
        params: Any | None = None,
        *,
        tolerate_errors: bool = False,
    ) -> Any | None:
        """Return decoded JSON, or None when the resource does not exist.

        `tolerate_errors` turns a failure into None instead of an exception. It
        is for calls that improve an answer rather than make one: the hosted
        catalogue's search is slow enough to return a sporadic 504, and one
        timed-out lookup must not fail a fifty-line cart that has already
        resolved forty-nine of its lines.
        """
        circuit = _circuit_key(path)
        if tolerate_errors and self._circuit_open(circuit):
            return _FAILED

        attempts = CATALOG_RETRY_ATTEMPTS
        last: str = "unknown"
        for attempt in range(attempts):
            try:
                response = self._request(path, params)
            except httpx.HTTPError as exc:
                last = type(exc).__name__
            else:
                if response.status_code == 404:
                    self._record_success(circuit)
                    return None
                if response.status_code < 400:
                    try:
                        payload = response.json()
                    except ValueError as exc:
                        if tolerate_errors:
                            self._record_failure(circuit)
                            return _FAILED
                        raise CatalogUnavailableError(
                            f"the price database returned a non-JSON body for {path}"
                        ) from exc
                    self._record_success(circuit)
                    return payload
                last = str(response.status_code)
                # 4xx is a bad request, not bad luck; retrying repeats it.
                if response.status_code < 500:
                    break
            if attempt + 1 < attempts:
                # Another thread may have tripped the breaker while this call
                # was in flight; with sixteen workers against a dead host, not
                # re-checking here doubles the time before anything gives up.
                if tolerate_errors and self._circuit_open(circuit):
                    break
                time.sleep(CATALOG_RETRY_BACKOFF_SECONDS * (attempt + 1))

        self._record_failure(circuit)
        if tolerate_errors:
            logger.warning("tolerated catalogue failure for %s (%s)", path, last)
            return _FAILED
        raise CatalogUnavailableError(
            f"the price database returned {last} for {path}"
        )

    # -- circuit breaker -----------------------------------------------------

    def _circuit_open(self, circuit: str) -> bool:
        """Whether to stop calling an endpoint that is plainly down.

        Without this, a fifty-line receipt against a dead service is fifty
        lookups times two attempts times a thirty-second timeout — the user
        waits minutes to be told nothing. After a run of consecutive failures
        the remaining calls are skipped, and one is let through periodically to
        notice when the service comes back.

        Tracked per endpoint, because on this API they fail independently:
        `/products/search` 504s reliably while `/products/barcode` answers every
        time. One shared counter lets the dead endpoint trip the breaker for the
        working one, which turns a receipt that could be half-priced into one
        that is not priced at all.
        """
        with self._lock:
            if self._failures.get(circuit, 0) < CIRCUIT_BREAKER_THRESHOLD:
                return False
            opened = self._opened_at.get(circuit, 0.0)
            if (time.monotonic() - opened) >= CIRCUIT_BREAKER_COOLDOWN_SECONDS:
                # Half-open: let one call through and see. Stepping back to just
                # below the threshold rather than resetting means a single
                # failure re-opens it — a host that has been down for an hour
                # should cost one probe per cooldown, not another full run of
                # timeouts before we believe it again.
                self._failures[circuit] = CIRCUIT_BREAKER_THRESHOLD - 1
                self._opened_at[circuit] = time.monotonic()
                return False
            return True

    def _record_success(self, circuit: str) -> None:
        with self._lock:
            self._failures[circuit] = 0

    def _record_failure(self, circuit: str) -> None:
        with self._lock:
            count = self._failures.get(circuit, 0) + 1
            self._failures[circuit] = count
            if count == CIRCUIT_BREAKER_THRESHOLD:
                self._opened_at[circuit] = time.monotonic()
                logger.warning(
                    "%s%s failed %d times in a row; pausing it for %ds",
                    self._base_url,
                    circuit,
                    count,
                    int(CIRCUIT_BREAKER_COOLDOWN_SECONDS),
                )

    def find_product(self, barcode: str) -> ProductLookup:
        """Look one barcode up, saying whether the database actually answered.

        Cached for the process: a barcode maps to the same catalogue row for
        far longer than a session, the hosted service takes seconds per lookup,
        and the same staples recur across every receipt a shopper scans.
        """
        with self._lock:
            cached = self._products.get(barcode, _MISSING)
        if cached is not _MISSING:
            return ProductLookup(cached, True)  # type: ignore[arg-type]

        payload = self._get(f"/products/barcode/{barcode}", tolerate_errors=True)
        if payload is _FAILED:
            # We never got an answer, so we have learned nothing. Caching this
            # as "absent" would keep the product missing for the whole process.
            return ProductLookup(None, False)

        product = None
        if isinstance(payload, dict):
            found = payload.get("product")
            product = found if isinstance(found, dict) else None
        with self._lock:
            self._products[barcode] = product
        return ProductLookup(product, True)

    def product_by_barcode(self, barcode: str) -> dict[str, Any] | None:
        """The product for a barcode, or None whether absent or unreachable."""
        return self.find_product(barcode).product

    def search_products(
        self,
        query: str,
        *,
        limit: int = SEARCH_CANDIDATE_LIMIT,
    ) -> list[dict[str, Any]]:
        """Substring-search product names; an empty result is not an error."""
        if not query.strip():
            return []
        payload = self._get(
            "/products/search",
            {"query": query, "limit": limit},
            tolerate_errors=True,
        )
        if not isinstance(payload, dict):
            return []
        items = payload.get("items")
        return [item for item in items if isinstance(item, dict)] if items else []

    def similar_products(
        self,
        product_id: str,
        *,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Fetch similar products by item_code."""
        payload = self._get(
            "/products/similar",
            {"item_code": product_id, "limit": limit},
            tolerate_errors=True,
        )
        if not isinstance(payload, list):
            return []
        return [item for item in payload if isinstance(item, dict)]

    def compare_prices(
        self,
        product_ids: list[str],
        *,
        current_only: bool = True,
    ) -> list[dict[str, Any]]:
        """Fetch price comparisons for any number of products, 20 at a time.

        A batch that fails costs the cart the twenty products in it, not the
        whole comparison — but if *every* batch fails the caller has no prices
        at all, and saying so beats returning an empty cart that reads like
        "nothing you bought is sold anywhere".
        """
        batches = [
            product_ids[start : start + MAX_PRODUCT_IDS_PER_REQUEST]
            for start in range(0, len(product_ids), MAX_PRODUCT_IDS_PER_REQUEST)
        ]
        if not batches:
            return []

        def fetch(batch: list[str]) -> Any | None:
            return self._get(
                "/products/compare-prices",
                {"product_ids": batch, "current_only": current_only},
                tolerate_errors=True,
            )

        if len(batches) == 1:
            payloads = [fetch(batches[0])]
        else:
            with ThreadPoolExecutor(max_workers=BARCODE_LOOKUP_WORKERS) as pool:
                payloads = list(pool.map(fetch, batches))

        comparisons: list[dict[str, Any]] = []
        answered = 0
        for payload in payloads:
            if not isinstance(payload, dict):
                continue
            answered += 1
            found = payload.get("comparisons")
            if found:
                comparisons.extend(entry for entry in found if isinstance(entry, dict))

        if answered == 0:
            raise CatalogUnavailableError(
                "the price database answered none of the "
                f"{len(batches)} price requests for this cart"
            )
        return comparisons

    def stores(
        self,
        *,
        city: str | None = None,
        chain_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """List stores, optionally narrowed to a city or a chain.

        Unfiltered the endpoint caps its response, so a caller that wants full
        coverage narrows by chain or city rather than paging.
        """
        params: dict[str, Any] = {}
        if city:
            params["city"] = city
        if chain_id:
            params["chain_id"] = chain_id
        payload = self._get("/stores/", params or None, tolerate_errors=True)
        if not isinstance(payload, dict):
            return []
        found = payload.get("stores")
        return [store for store in found if isinstance(store, dict)] if found else []

    def stores_nearby(
        self,
        lat: float,
        lng: float,
        radius_m: float,
        *,
        chain_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Branches within `radius_m` of a point.

        The one store query that takes coordinates. It caps its response at 100
        rows and does not sort them, so the caller sorts by distance itself —
        but it filters the radius honestly, which `/stores/` cannot do at all.
        """
        params: dict[str, Any] = {"lat": lat, "lng": lng, "radius": radius_m}
        if chain_id:
            params["chain_id"] = chain_id
        payload = self._get("/stores/nearby", params, tolerate_errors=True)
        if not isinstance(payload, dict):
            return []
        found = payload.get("stores")
        return [store for store in found if isinstance(store, dict)] if found else []

    def chains(self) -> list[dict[str, Any]]:
        """List chains with their store counts."""
        payload = self._get("/chains/", tolerate_errors=True)
        if not isinstance(payload, dict):
            return []
        found = payload.get("chains")
        if not found:
            return []
        return [
            entry["chain"]
            for entry in found
            if isinstance(entry, dict) and isinstance(entry.get("chain"), dict)
        ]


_DEFAULT: SupermarketsCatalog | None = None
_DEFAULT_LOCK = threading.Lock()


def default_catalog() -> SupermarketsCatalog:
    """The process-wide catalogue.

    Everything that makes this client usable is per-instance state — the
    connection pool, the barcode cache, the circuit breaker — so building one
    per request throws all three away each time. The pool matters most: a fresh
    instance means a cold TLS handshake per product, which is the shape of load
    the hosted service refuses.
    """
    global _DEFAULT
    with _DEFAULT_LOCK:
        if _DEFAULT is None:
            _DEFAULT = SupermarketsCatalog()
        return _DEFAULT


__all__ = [
    "CatalogUnavailableError",
    "ProductLookup",
    "SupermarketsCatalog",
    "default_catalog",
]
