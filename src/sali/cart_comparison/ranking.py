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


def _line_barcodes(line: MatchedLine) -> list[int]:
    """Every barcode that reads this line equally well, primary first."""
    return [
        line.product.barcode,
        *(alternate.product.barcode for alternate in line.alternates),
    ]


def rank_carts(
    matched: list[MatchedLine],
    prices: list[StorePrice],
    *,
    stores: dict[str, dict[str, Any]] | None = None,
    city: str | None = None,
) -> tuple[list[StoreCart], list[StoreCart]]:
    """Return (complete carts, partial carts), each cheapest first."""
    directory = stores or {}
    wanted = {
        barcode
        for line in matched
        if line.matched_by != "fixed_charge"
        for barcode in _line_barcodes(line)
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

    chain_prices = {
        chain_id: priced
        for (chain_id, store_id), priced in by_store.items()
        if store_id is None
    }

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

        # A line counts as priced when any of its readings is: the store that
        # keys the same produce under its own code still supplies the line.
        total = Decimal(0)
        priced_lines = 0
        missing: list[MissingProduct] = []
        used_chain_estimate = sample.chain_level
        for line in matched:
            if line.matched_by == "fixed_charge":
                priced_lines += 1
                total += Decimal(line.paid)
                continue
            quotes = [
                price
                for barcode in _line_barcodes(line)
                if (price := priced.get(barcode)) is not None
            ]
            if not quotes and store_id is not None:
                fallback = chain_prices.get(chain_id, {})
                quotes = [
                    price
                    for barcode in _line_barcodes(line)
                    if (price := fallback.get(barcode)) is not None
                ]
                used_chain_estimate = used_chain_estimate or bool(quotes)
            if quotes:
                priced_lines += 1
                total += _quantity(line) * min(quote.price for quote in quotes)
            else:
                missing.append(
                    MissingProduct(barcode=line.product.barcode, name=line.product.name)
                )

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
            priced_items=priced_lines,
            total_items=len(matched),
            missing=missing,
            total=_money(total),
            chain_level_estimate=used_chain_estimate,
        )
        (complete if cart.complete else partial).append(cart)

    complete.sort(key=lambda cart: Decimal(cart.total))
    # A partial cart is only interesting for what it does cover, so coverage
    # outranks price: 11 of 12 items for a little more beats 6 for half.
    partial.sort(key=lambda cart: (-cart.priced_items, Decimal(cart.total)))
    return complete, partial


__all__ = ["rank_carts", "store_directory"]
