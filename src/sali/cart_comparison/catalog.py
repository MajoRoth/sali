"""Client for the Open Supermarkets price database.

The endpoints this talks to are read-only, so the client's whole job is shape:
batching `compare-prices` under its 20-id ceiling, turning a 404 into "no such
product" rather than an exception, and never letting one slow upstream call
fail a whole cart.

Speed is the other half of the job. The hosted service answers a single barcode
lookup in about five seconds, which is fine for one product and useless for a
fifty-line receipt — so lookups run concurrently and their results are cached
for the life of the process.
"""

from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import httpx

from sali.cart_comparison.configuration import (
    BARCODE_LOOKUP_WORKERS,
    CATALOG_RETRY_ATTEMPTS,
    CATALOG_RETRY_BACKOFF_SECONDS,
    CATALOG_TIMEOUT_SECONDS,
    CIRCUIT_BREAKER_COOLDOWN_SECONDS,
    CIRCUIT_BREAKER_THRESHOLD,
    MAX_PRODUCT_IDS_PER_REQUEST,
    SEARCH_CANDIDATE_LIMIT,
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


class CatalogUnavailableError(RuntimeError):
    """The price database could not be reached or answered unusably."""


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
        self._products: dict[str, dict[str, Any] | None] = {}
        self._lock = threading.Lock()
        self._failures = 0
        self._opened_at = 0.0

    def _request(
        self,
        path: str,
        params: Any | None = None,
    ) -> httpx.Response:
        if self._client is not None:
            return self._client.get(
                f"{self._base_url}{path}",
                params=params,
                headers=self._headers,
                timeout=CATALOG_TIMEOUT_SECONDS,
            )
        with httpx.Client(timeout=CATALOG_TIMEOUT_SECONDS) as client:
            return client.get(
                f"{self._base_url}{path}",
                params=params,
                headers=self._headers,
            )

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
        if tolerate_errors and self._circuit_open():
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
                    self._record_success()
                    return None
                if response.status_code < 400:
                    try:
                        payload = response.json()
                    except ValueError as exc:
                        if tolerate_errors:
                            self._record_failure()
                            return _FAILED
                        raise CatalogUnavailableError(
                            f"the price database returned a non-JSON body for {path}"
                        ) from exc
                    self._record_success()
                    return payload
                last = str(response.status_code)
                # 4xx is a bad request, not bad luck; retrying repeats it.
                if response.status_code < 500:
                    break
            if attempt + 1 < attempts:
                # Another thread may have tripped the breaker while this call
                # was in flight; with sixteen workers against a dead host, not
                # re-checking here doubles the time before anything gives up.
                if tolerate_errors and self._circuit_open():
                    break
                time.sleep(CATALOG_RETRY_BACKOFF_SECONDS * (attempt + 1))

        self._record_failure()
        if tolerate_errors:
            logger.warning("tolerated catalogue failure for %s (%s)", path, last)
            return _FAILED
        raise CatalogUnavailableError(
            f"the price database returned {last} for {path}"
        )

    # -- circuit breaker -----------------------------------------------------

    def _circuit_open(self) -> bool:
        """Whether to stop calling a host that is plainly down.

        Without this, a fifty-line receipt against a dead service is fifty
        lookups times two attempts times a thirty-second timeout — the user
        waits minutes to be told nothing. After a run of consecutive failures
        the remaining calls are skipped, and one is let through periodically to
        notice when the service comes back.
        """
        with self._lock:
            if self._failures < CIRCUIT_BREAKER_THRESHOLD:
                return False
            if (time.monotonic() - self._opened_at) >= CIRCUIT_BREAKER_COOLDOWN_SECONDS:
                # Half-open: let one call through and see. Stepping back to just
                # below the threshold rather than resetting means a single
                # failure re-opens it — a host that has been down for an hour
                # should cost one probe per cooldown, not another full run of
                # timeouts before we believe it again.
                self._failures = CIRCUIT_BREAKER_THRESHOLD - 1
                self._opened_at = time.monotonic()
                return False
            return True

    def _record_success(self) -> None:
        with self._lock:
            self._failures = 0

    def _record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self._failures == CIRCUIT_BREAKER_THRESHOLD:
                self._opened_at = time.monotonic()
                logger.warning(
                    "%s failed %d times in a row; pausing calls for %ds",
                    self._base_url,
                    self._failures,
                    int(CIRCUIT_BREAKER_COOLDOWN_SECONDS),
                )

    def product_by_barcode(self, barcode: str) -> dict[str, Any] | None:
        """Look one barcode up exactly; None when the catalogue has no such row.

        Cached for the process: a barcode maps to the same catalogue row for
        far longer than a session, the hosted service takes seconds per lookup,
        and the same staples recur across every receipt a shopper scans.
        """
        with self._lock:
            cached = self._products.get(barcode, _MISSING)
        if cached is not _MISSING:
            return cached  # type: ignore[return-value]

        payload = self._get(f"/products/barcode/{barcode}", tolerate_errors=True)
        if payload is _FAILED:
            # We never got an answer, so we have learned nothing. Caching this
            # as "absent" would keep the product missing for the whole process.
            return None

        product = None
        if isinstance(payload, dict):
            found = payload.get("product")
            product = found if isinstance(found, dict) else None
        with self._lock:
            self._products[barcode] = product
        return product

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


__all__ = ["CatalogUnavailableError", "SupermarketsCatalog"]
