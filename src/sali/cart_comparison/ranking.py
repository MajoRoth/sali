"""Turn per-store prices into the ranked answer a shopper asked for.

The rule is the shopper's: a store that cannot supply the whole cart is not a
cheaper option, it is a different errand. So stores carrying every matched
product are ranked first, cheapest first, and stores missing something are
ranked below them rather than mixed in — because a cart missing its two most
expensive lines is always "cheapest", and always wrong.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sali.cart_comparison.models import MatchedLine, MissingProduct, StoreCart
from sali.cart_comparison.pricing import StorePrice

_CENTS = Decimal("0.01")


def _money(value: Decimal) -> str:
    return str(value.quantize(_CENTS, rounding=ROUND_HALF_UP))


def _quantity(line: MatchedLine) -> Decimal:
    quantity = Decimal(line.quantity)
    # A line the receipt could not quantify still costs one of something.
    return quantity if quantity > 0 else Decimal(1)


def store_directory(stores: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Index stores by id so a price row can be given a name and an address."""
    directory: dict[str, dict[str, Any]] = {}
    for store in stores:
        identifier = store.get("id")
        if isinstance(identifier, str) and identifier:
            directory[identifier] = store
    return directory


def rank_carts(
    matched: list[MatchedLine],
    prices: list[StorePrice],
    *,
    stores: dict[str, dict[str, Any]] | None = None,
    city: str | None = None,
) -> tuple[list[StoreCart], list[StoreCart]]:
    """Return (complete carts, partial carts), each cheapest first."""
    directory = stores or {}
    wanted: dict[int, str] = {
        line.product.barcode: line.product.name for line in matched
    }
    if not wanted or not prices:
        return [], []

    # Cheapest wins when a store quotes a product more than once.
    by_store: dict[tuple[str, str | None], dict[int, StorePrice]] = defaultdict(dict)
    for price in prices:
        if price.barcode not in wanted:
            continue
        bucket = by_store[(price.chain_id, price.store_id)]
        current = bucket.get(price.barcode)
        if current is None or price.price < current.price:
            bucket[price.barcode] = price

    complete: list[StoreCart] = []
    partial: list[StoreCart] = []

    for (chain_id, store_id), priced in by_store.items():
        sample = next(iter(priced.values()))
        record = directory.get(store_id or "", {})
        address = record.get("address") if isinstance(record, dict) else None
        address = address if isinstance(address, dict) else {}

        store_city = sample.city or (address.get("city") if address else None)
        if city and store_city and store_city.strip() != city.strip():
            continue

        total = Decimal(0)
        for line in matched:
            price = priced.get(line.product.barcode)
            if price is not None:
                total += _quantity(line) * price.price

        missing = [
            MissingProduct(barcode=barcode, name=name)
            for barcode, name in wanted.items()
            if barcode not in priced
        ]
        cart = StoreCart(
            store_id=store_id,
            store_name=sample.store_name
            or (record.get("storeName") if isinstance(record, dict) else None),
            city=store_city,
            address=(address.get("storeAddress") if address else None)
            or sample.address,
            chain_id=chain_id,
            chain_name=sample.chain_name,
            complete=not missing,
            priced_items=len(priced),
            total_items=len(wanted),
            total=_money(total),
            missing=missing,
            chain_level_estimate=sample.chain_level,
        )
        (complete if cart.complete else partial).append(cart)

    complete.sort(key=lambda cart: Decimal(cart.total))
    # A partial cart is only interesting for what it does cover, so coverage
    # outranks price: 11 of 12 items for a little more beats 6 for half.
    partial.sort(key=lambda cart: (-cart.priced_items, Decimal(cart.total)))
    return complete, partial


__all__ = ["rank_carts", "store_directory"]
