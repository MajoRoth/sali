"""Client for the Open Supermarkets price database.

The endpoints this talks to are read-only and unauthenticated, so the client's
whole job is shape: batching `compare-prices` under its 20-id ceiling, turning
a 404 into "no such product" rather than an exception, and never letting one
slow upstream call fail a whole cart.
"""

from __future__ import annotations

from typing import Any

import httpx

from sali.cart_comparison.configuration import (
    CATALOG_TIMEOUT_SECONDS,
    MAX_PRODUCT_IDS_PER_REQUEST,
    SEARCH_CANDIDATE_LIMIT,
    catalog_base_url,
)


class CatalogUnavailableError(RuntimeError):
    """The price database could not be reached or answered unusably."""


class SupermarketsCatalog:
    """Read products, prices, and stores from the Open Supermarkets API."""

    def __init__(
        self,
        base_url: str | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self._base_url = (base_url or catalog_base_url()).rstrip("/")
        self._client = client

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any | None:
        """Return decoded JSON, or None when the resource does not exist."""
        try:
            if self._client is not None:
                response = self._client.get(
                    f"{self._base_url}{path}",
                    params=params,
                    timeout=CATALOG_TIMEOUT_SECONDS,
                )
            else:
                with httpx.Client(timeout=CATALOG_TIMEOUT_SECONDS) as client:
                    response = client.get(f"{self._base_url}{path}", params=params)
        except httpx.HTTPError as exc:
            raise CatalogUnavailableError(
                f"the price database could not be reached ({type(exc).__name__})"
            ) from exc

        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            raise CatalogUnavailableError(
                f"the price database returned {response.status_code} for {path}"
            )
        try:
            return response.json()
        except ValueError as exc:
            raise CatalogUnavailableError(
                f"the price database returned a non-JSON body for {path}"
            ) from exc

    def product_by_barcode(self, barcode: str) -> dict[str, Any] | None:
        """Look one barcode up exactly; None when the catalogue has no such row."""
        payload = self._get(f"/products/barcode/{barcode}")
        if not isinstance(payload, dict):
            return None
        product = payload.get("product")
        return product if isinstance(product, dict) else None

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
        """Fetch price comparisons for any number of products, 20 at a time."""
        comparisons: list[dict[str, Any]] = []
        for start in range(0, len(product_ids), MAX_PRODUCT_IDS_PER_REQUEST):
            batch = product_ids[start : start + MAX_PRODUCT_IDS_PER_REQUEST]
            payload = self._get(
                "/products/compare-prices",
                {"product_ids": batch, "current_only": current_only},
            )
            if not isinstance(payload, dict):
                continue
            found = payload.get("comparisons")
            if found:
                comparisons.extend(entry for entry in found if isinstance(entry, dict))
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
        payload = self._get("/stores/", params or None)
        if not isinstance(payload, dict):
            return []
        found = payload.get("stores")
        return [store for store in found if isinstance(store, dict)] if found else []

    def chains(self) -> list[dict[str, Any]]:
        """List chains with their store counts."""
        payload = self._get("/chains/")
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
