"""Read prices out of the price database's comparison payload.

`compare-prices` types its chain-level figures but leaves each chain's
`storePrices` as free-form objects, so the per-store reader accepts the field
names the rest of that API uses and tolerates the ones it does not. When a chain
returns no per-store breakdown at all, its own cheapest price still places the
chain in the ranking — flagged, so a chain-level estimate is never mistaken for
a price a specific branch quoted.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

#: Field names seen for the same value across this API's payloads. Ordered by
#: preference: an explicit current price beats a generic one.
_PRICE_KEYS = ("price", "currentPrice", "itemPrice", "unitPrice", "value")
_STORE_ID_KEYS = ("storeId", "store_id", "id", "storeNumber", "store_number")
_STORE_NAME_KEYS = ("storeName", "store_name", "name", "branchName")
_CITY_KEYS = ("city", "storeCity")
_ADDRESS_KEYS = ("storeAddress", "address", "street")


@dataclass(frozen=True)
class StorePrice:
    """One product's price at one identified store."""

    barcode: int
    chain_id: str
    chain_name: str
    store_id: str | None
    store_name: str | None
    city: str | None
    address: str | None
    price: Decimal
    #: True when the figure is the chain's cheapest rather than this store's own.
    chain_level: bool


def _first_text(source: dict[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = source.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, int) and not isinstance(value, bool):
            return str(value)
    return None


def _first_price(source: dict[str, Any], keys: Iterable[str]) -> Decimal | None:
    for key in keys:
        value = source.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, int | float):
            price = Decimal(str(value))
            return price if price > 0 else None
        if isinstance(value, str) and value.strip():
            try:
                price = Decimal(value.strip())
            except InvalidOperation:
                continue
            return price if price > 0 else None
    return None


def _nested_address(entry: dict[str, Any]) -> dict[str, Any]:
    nested = entry.get("address")
    return nested if isinstance(nested, dict) else {}


def read_store_prices(comparisons: Iterable[dict[str, Any]]) -> list[StorePrice]:
    """Flatten `compare-prices` output into one row per store per product."""
    prices: list[StorePrice] = []

    for comparison in comparisons:
        barcode = comparison.get("productBarcode")
        if not isinstance(barcode, int):
            continue
        chains = comparison.get("chainComparison")
        if not isinstance(chains, list):
            continue

        for chain in chains:
            if not isinstance(chain, dict):
                continue
            chain_id = chain.get("chainId")
            if not isinstance(chain_id, str) or not chain_id:
                continue
            chain_name = str(chain.get("chainName") or chain_id)
            store_entries = chain.get("storePrices")
            store_entries = store_entries if isinstance(store_entries, list) else []

            resolved = 0
            for entry in store_entries:
                if not isinstance(entry, dict):
                    continue
                price = _first_price(entry, _PRICE_KEYS)
                if price is None:
                    continue
                address = _nested_address(entry)
                prices.append(
                    StorePrice(
                        barcode=barcode,
                        chain_id=chain_id,
                        chain_name=chain_name,
                        store_id=_first_text(entry, _STORE_ID_KEYS),
                        store_name=_first_text(entry, _STORE_NAME_KEYS),
                        city=_first_text(entry, _CITY_KEYS)
                        or _first_text(address, _CITY_KEYS),
                        address=_first_text(entry, _ADDRESS_KEYS)
                        or _first_text(address, _ADDRESS_KEYS),
                        price=price,
                        chain_level=False,
                    )
                )
                resolved += 1

            # Keep the chain's own minimum even when branch rows exist. Price
            # feeds are often sparse per branch: branch A lists the milk and
            # branch B lists the bread although the chain carries both. The
            # chain row lets cart assembly fill such a branch-level gap while
            # explicitly marking the result as an estimate.
            chain_price = _first_price(chain, ("minPrice", "avgPrice"))
            if chain_price is not None:
                prices.append(
                    StorePrice(
                        barcode=barcode,
                        chain_id=chain_id,
                        chain_name=chain_name,
                        store_id=None,
                        store_name=None,
                        city=None,
                        address=None,
                        price=chain_price,
                        chain_level=True,
                    )
                )

    return prices


__all__ = ["StorePrice", "read_store_prices"]
