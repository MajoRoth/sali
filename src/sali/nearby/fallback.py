"""Simulated prices, for when the price database has nothing to say.

Both deployments of the Open Supermarkets API can be — and at the time of
writing both are — unable to price a cart: the production instance times out or
500s on every endpoint, and the open instance's price pipeline has never run
(`/health/pipeline` reports zero chains). With no prices anywhere, the
comparison screens have nothing to render and the app cannot be demonstrated,
reviewed, or developed against.

This module fills that gap, and it is important to be exact about what it is:

**These are not real prices, and they must never be presented as real.** They
are derived from the shopper's own receipt — the price they actually paid,
varied per store by a deterministic hash — so the screens have plausibly-shaped
data to lay out. A saving computed from them is arithmetic on invented numbers.

Two things follow, and both are enforced rather than documented:

* It is **off unless asked for**, via `SALI_FALLBACK_PRICES`. A deployment that
  does nothing gets an honest "no prices available", never a quiet simulation.
* Every response it touches carries a `demo prices:` warning, and every store it
  builds is flagged `simulated`, so the UI can label the screen and does not
  have to infer anything.

The real fix is upstream price data. This is scaffolding, and it is built to be
deleted.
"""

from __future__ import annotations

import hashlib
import os
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from sali.nearby.models import Cart, CartLine, GeoPoint, NearbyStore, OptimalCart
from sali.nearby.stores import NearbyRecord
from sali.nearby.units import normalize_unit
from sali.receipt_extraction.models import ReceiptDocument

_CENTS = Decimal("0.01")

#: The warning every simulated response carries. The UI keys off this prefix.
DEMO_WARNING = (
    "demo prices: the price database is unavailable, so the figures shown are "
    "simulated from your own receipt and are not real shelf prices"
)

#: How far a simulated store price may stray from what was paid, either way.
#: Wide enough that stores visibly differ, narrow enough to stay plausible.
_SPREAD = Decimal("0.14")

#: Roughly how often a simulated store simply does not stock a line. Real carts
#: are rarely fully covered anywhere, and a UI that never sees a missing line is
#: a UI whose missing-line handling was never exercised.
_UNAVAILABLE_IN = 17


def enabled() -> bool:
    """Whether simulated prices may stand in for a dead price database."""
    return os.environ.get("SALI_FALLBACK_PRICES", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _money(value: Decimal) -> float:
    return float(value.quantize(_CENTS, rounding=ROUND_HALF_UP))


def _decimal(value: str | None, fallback: Decimal = Decimal(0)) -> Decimal:
    if value is None:
        return fallback
    try:
        return Decimal(value)
    except InvalidOperation:
        return fallback


def _ratio(*parts: str) -> Decimal:
    """A stable number in 0.0-1.0 from the given strings.

    Hashed rather than randomised so a store's price does not change between two
    renders of the same screen — a comparison whose numbers move when you look
    away is worse than no comparison.
    """
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).digest()
    return Decimal(int.from_bytes(digest[:4], "big")) / Decimal(0xFFFFFFFF)


def simulated_stores(
    document: ReceiptDocument,
    in_radius: list[NearbyRecord],
    *,
    limit: int,
    include_online: bool = False,
) -> list[NearbyStore]:
    """Build store carts from the receipt itself, for a dead price database.

    The branches are real — names, chains, and coordinates come from the store
    directory. Only the money is invented.
    """
    items = [item for item in document.receipt.items if item.name]
    if not items or not in_radius:
        return []

    built: list[NearbyStore] = []
    for record in in_radius[:limit]:
        store = record.store
        # One factor per store, so a cheap shop is cheap across the whole cart
        # rather than randomly cheap line by line.
        store_bias = (_ratio(store.chain_id, store.store_id) - Decimal("0.5")) * _SPREAD

        lines: list[CartLine] = []
        total = Decimal(0)
        unavailable = 0

        for index, item in enumerate(items):
            paid = _decimal(item.final_total)
            quantity = _decimal(item.quantity, Decimal(1))
            if quantity <= 0:
                quantity = Decimal(1)
            unit_paid = paid / quantity if paid > 0 else Decimal(0)

            key = item.code or f"{store.store_id}:{index}"
            if int(_ratio(store.store_id, key, "stock") * 100) % _UNAVAILABLE_IN == 0:
                unavailable += 1
                lines.append(
                    CartLine(
                        position=item.position,
                        barcode=str(item.code or ""),
                        name=item.name,
                        qty=float(quantity),
                        unit=normalize_unit(item.unit),
                        unit_price=None,
                        line_total=None,
                        available=False,
                    )
                )
                continue

            jitter = (_ratio(store.store_id, key) - Decimal("0.5")) * _SPREAD
            unit_price = unit_paid * (Decimal(1) + store_bias + jitter)
            if unit_price <= 0:
                unit_price = unit_paid if unit_paid > 0 else _CENTS
            line_total = unit_price * quantity
            total += line_total
            lines.append(
                CartLine(
                    position=item.position,
                    barcode=str(item.code or ""),
                    name=item.name,
                    qty=float(quantity),
                    unit=normalize_unit(item.unit),
                    unit_price=_money(unit_price),
                    line_total=_money(line_total),
                    available=True,
                )
            )

        coverage = round((len(items) - unavailable) / len(items), 4)
        cart = Cart(
            items=lines,
            total=_money(total),
            unavailable_count=unavailable,
            coverage=coverage,
        )
        built.append(
            NearbyStore(
                store_id=store.store_id,
                chain=store.chain_name,
                branch=store.store_name or store.chain_name,
                online=False,
                location=(
                    GeoPoint(lat=store.lat, lng=store.lng)
                    if store.located and store.lat is not None and store.lng is not None
                    else None
                ),
                distance_m=round(record.distance_m, 1),
                delivery_fee=0.0,
                city=store.city,
                address=store.address,
                chain_level_estimate=False,
                simulated=True,
                same_cart=cart,
                # No swaps: a substitution is a recommendation to buy something
                # different, and recommending that on invented prices is the one
                # thing this module must not do.
                optimal_cart=OptimalCart(
                    items=lines,
                    total=cart.total,
                    unavailable_count=unavailable,
                    coverage=coverage,
                    swaps=[],
                    savings_vs_same_cart=0.0,
                ),
            )
        )

    built.sort(key=lambda store: (-store.same_cart.coverage, store.same_cart.total))
    return built


__all__ = ["DEMO_WARNING", "enabled", "simulated_stores"]
