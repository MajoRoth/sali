"""Assemble the answer the app's three screens render.

This is where a receipt, a price database, and a pair of coordinates become one
object: what was bought, what it would cost at each shop within walking reach,
where it was actually bought, and — said out loud rather than implied by an
empty list — what could not be worked out.

The ordering rule is the shopper's, and it is the same rule cart comparison
uses: a store that cannot supply the cart is not a cheaper option, it is a
different errand. Coverage outranks price, always.
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from sali.cart_comparison.catalog import (
    CatalogUnavailableError,
    SupermarketsCatalog,
    default_catalog,
)
from sali.cart_comparison.configuration import CONFIDENT_NAME_MATCH_SCORE
from sali.cart_comparison.matching import CartMatcher
from sali.cart_comparison.models import CatalogProduct, MatchedLine, UnmatchedLine
from sali.cart_comparison.pricing import StorePrice, read_store_prices
from sali.nearby import fallback
from sali.nearby.geo import distance_meters
from sali.nearby.models import (
    Cart,
    CartLine,
    GeoPoint,
    NearbyResponse,
    NearbyStore,
    OptimalCart,
    Swap,
    UnmatchedCartLine,
)
from sali.nearby.stores import NearbyRecord, StoreDirectory, default_directory
from sali.nearby.swaps import AppliedSwap, choose_swaps, find_candidates
from sali.nearby.units import normalize_unit
from sali.receipt_extraction.models import Item, ReceiptDocument

logger = logging.getLogger(__name__)

_CENTS = Decimal("0.01")


def _money(value: Decimal) -> float:
    return float(value.quantize(_CENTS, rounding=ROUND_HALF_UP))


def _decimal(value: str | None, fallback: Decimal = Decimal(0)) -> Decimal:
    if value is None:
        return fallback
    try:
        return Decimal(value)
    except InvalidOperation:
        return fallback


def _quantity(item: Item) -> Decimal:
    """How many of a line were bought; a line the receipt could not quantify
    still cost one of something."""
    quantity = _decimal(item.quantity, Decimal(1))
    return quantity if quantity > 0 else Decimal(1)


def _cheapest_reading(
    line: MatchedLine,
    store_prices: dict[int, Decimal],
) -> tuple[CatalogProduct, float | None, Decimal] | None:
    """How this store sells this line, if it does: the cheapest priced product
    among the match and its equally-valid alternates.

    The alternates are what let a line cross chains — each chain keys its own
    bananas on its own code, so the primary match alone can only ever be priced
    where it was matched. The store's cart line shows whichever product was
    actually priced, under that product's own name and confidence.
    """
    readings = [
        (line.product, line.confidence if line.matched_by == "name" else None),
        *((alternate.product, alternate.confidence) for alternate in line.alternates),
    ]
    best: tuple[CatalogProduct, float | None, Decimal] | None = None
    for product, confidence in readings:
        price = store_prices.get(product.barcode)
        if price is None:
            continue
        if best is None or price < best[2]:
            best = (product, confidence, price)
    return best


class NearbyService:
    """Price one receipt's cart against the stores around a shopper."""

    def __init__(
        self,
        catalog: SupermarketsCatalog | None = None,
        matcher: CartMatcher | None = None,
        directory: StoreDirectory | None = None,
    ) -> None:
        self._catalog = catalog or default_catalog()
        self._matcher = matcher or CartMatcher(self._catalog)
        self._directory = directory or default_directory()

    def price(
        self,
        document: ReceiptDocument,
        *,
        location: GeoPoint,
        radius_m: int,
        limit: int = 30,
        include_online: bool = False,
    ) -> NearbyResponse:
        here = (location.lat, location.lng)
        items = {item.position: item for item in document.receipt.items}
        matched, unmatched = self._resolve(document)
        warnings: list[str] = []

        in_radius = self._directory.nearby(here, radius_m)
        if not in_radius:
            warnings.append(
                f"no supermarket branch is within {radius_m} m of you; widen the "
                "radius to see stores"
            )

        # A dead price database raises rather than returning nothing, so the
        # simulated path has to catch that too — otherwise the one situation
        # the fallback exists for is the one it never sees.
        try:
            stores = self._priced_stores(
                matched=matched,
                items=items,
                in_radius=in_radius,
                include_online=include_online,
                warnings=warnings,
                here=here,
                radius_m=radius_m,
            )
        except CatalogUnavailableError:
            if not fallback.enabled():
                raise
            logger.warning("price database unavailable; falling back to simulation")
            stores = []

        # Nothing could be priced. If simulated prices have been explicitly
        # switched on, stand them up so the screens have something to lay out —
        # loudly, and never as a substitute for a real answer.
        if not stores and fallback.enabled():
            stores = fallback.simulated_stores(
                document, in_radius, limit=limit, include_online=include_online
            )
            if stores:
                warnings.append(fallback.DEMO_WARNING)

        warnings.extend(
            self._quality_warnings(
                document,
                matched,
                unmatched,
                stores,
                simulated=any(store.simulated for store in stores),
            )
        )

        return NearbyResponse(
            computed_at=datetime.now(UTC).isoformat(timespec="seconds"),
            currency=document.receipt.transaction.currency or "ILS",
            origin=self._origin(document, here, items),
            stores=stores[:limit],
            unmatched=[
                UnmatchedCartLine(
                    position=line.position,
                    name=line.receipt_name,
                    code=line.receipt_code,
                    paid=_money(_decimal(line.paid)),
                    reason=line.reason,
                )
                for line in unmatched
            ],
            warnings=warnings,
            stores_in_radius=len(in_radius),
        )

    def _priced_stores(
        self,
        *,
        matched: list[MatchedLine],
        items: dict[int, Item],
        in_radius: list[NearbyRecord],
        include_online: bool,
        warnings: list[str],
        here: tuple[float, float],
        radius_m: float,
    ) -> list[NearbyStore]:
        """The real answer: carts priced from the price database."""
        prices = self._read_prices(matched)
        if matched and not prices:
            warnings.append(
                "no store prices: the price database has no current listings for "
                "any matched product, so no cart could be priced"
            )

        swap_options = find_candidates(self._catalog, matched) if prices else []
        if swap_options:
            prices += self._read_prices_for(
                [option.product.product_id for option in swap_options]
            )

        built = self._build_stores(
            matched=matched,
            items=items,
            prices=prices,
            in_radius=in_radius,
            swap_options=swap_options,
            include_online=include_online,
            here=here,
            radius_m=radius_m,
        )

        if prices and not built:
            # Prices came back, but not one of the branches quoting them could be
            # placed near the shopper. Worth saying as its own thing: it is a
            # different problem from "nothing you bought is sold anywhere", and
            # an empty list alone implies the wrong one.
            quoted = len({(p.chain_id, p.store_id) for p in prices if p.store_id})
            warnings.append(
                f"prices were found at {quoted} branches, but none of them could "
                "be placed within your radius: the instance that publishes prices "
                "and the one that publishes coordinates do not cover the same "
                "chains"
            )

        if prices and in_radius:
            # The biggest chains publish no prices at all, so their branches sit
            # on the map unranked. Left unexplained, that reads as this app
            # ignoring the shopper's usual supermarket rather than as the data
            # gap it is.
            quoting_chains = {price.chain_id for price in prices}
            silent = sum(
                1 for record in in_radius if record.store.chain_id not in quoting_chains
            )
            if silent:
                warnings.append(
                    f"{silent} of {len(in_radius)} branches within your radius "
                    "belong to chains that published no price for any item on "
                    "this receipt, so they are shown on the map but cannot be "
                    "ranked"
                )

        return built

    # -- resolution ----------------------------------------------------------

    def _resolve(
        self,
        document: ReceiptDocument,
    ) -> tuple[list[MatchedLine], list[UnmatchedLine]]:
        matched: list[MatchedLine] = []
        unmatched: list[UnmatchedLine] = []

        items = list(document.receipt.items)
        for item, result in zip(items, self._matcher.match_all(items), strict=True):
            if result.product is None or result.matched_by is None:
                unmatched.append(
                    UnmatchedLine(
                        position=item.position,
                        receipt_name=item.name,
                        receipt_code=item.code,
                        paid=item.final_total,
                        reason=result.reason or "no catalogue product matched",
                    )
                )
                continue
            matched.append(
                MatchedLine(
                    position=item.position,
                    receipt_name=item.name,
                    receipt_code=item.code,
                    quantity=item.quantity or "1",
                    paid=item.final_total,
                    product=result.product,
                    matched_by=result.matched_by,
                    confidence=round(result.confidence, 3),
                    alternates=list(result.alternates),
                )
            )

        return matched, unmatched

    def _read_prices(self, matched: list[MatchedLine]) -> list[StorePrice]:
        if not matched:
            return []
        # Alternates are priced alongside the primary: a store that keys the
        # same produce under its own code can only be priced through them.
        return self._read_prices_for(
            list(
                dict.fromkeys(
                    product.product_id
                    for line in matched
                    for product in (
                        line.product,
                        *(alternate.product for alternate in line.alternates),
                    )
                )
            )
        )

    def _read_prices_for(self, product_ids: list[str]) -> list[StorePrice]:
        if not product_ids:
            return []
        return read_store_prices(self._catalog.compare_prices(product_ids))

    # -- store carts ---------------------------------------------------------

    def _build_stores(
        self,
        *,
        matched: list[MatchedLine],
        items: dict[int, Item],
        prices: list[StorePrice],
        in_radius: list[NearbyRecord],
        swap_options: list,
        include_online: bool,
        here: tuple[float, float],
        radius_m: float,
    ) -> list[NearbyStore]:
        if not matched or not prices:
            return []

        # Cheapest wins when one store quotes the same product twice.
        by_store: dict[tuple[str, str | None], dict[int, Decimal]] = defaultdict(dict)
        chain_names: dict[str, str] = {}
        for price in prices:
            chain_names.setdefault(price.chain_id, price.chain_name)
            bucket = by_store[(price.chain_id, price.store_id)]
            current = bucket.get(price.barcode)
            if current is None or price.price < current:
                bucket[price.barcode] = price.price

        reachable = {
            (record.store.chain_id, record.store.store_id): record
            for record in in_radius
        }
        # A store that quoted a price but is not in `in_radius` may still be
        # near: the map instance's listing is capped, and price coverage is thin
        # enough that the missing branch is often exactly the one that matters.
        # Locate it directly rather than dropping it.
        for key in by_store:
            if key in reachable or key[1] is None:
                continue
            found = self._directory.locate(key[0], key[1])
            if found is None:
                continue
            distance = distance_meters(here, (found.store.lat, found.store.lng))
            if distance <= radius_m:
                reachable[key] = NearbyRecord(found.store, distance)
        quantities = {
            line.position: _quantity(items[line.position])
            for line in matched
            if line.position in items
        }

        built: list[NearbyStore] = []
        for (chain_id, store_id), store_prices in by_store.items():
            record = reachable.get((chain_id, store_id))
            chain_level = store_id is None
            if record is None and not chain_level:
                # A priced branch outside the radius is a real shop, just not
                # one this shopper asked about.
                continue
            if chain_level and not include_online:
                continue

            built.append(
                self._store_cart(
                    matched=matched,
                    items=items,
                    quantities=quantities,
                    store_prices=store_prices,
                    swap_options=swap_options,
                    record=record,
                    chain_id=chain_id,
                    chain_name=chain_names.get(chain_id, chain_id),
                    store_id=store_id,
                    chain_level=chain_level,
                )
            )

        # Coverage first, then the optimal total: a cart that is cheap because it
        # is missing the expensive half is not the cheapest cart.
        built.sort(
            key=lambda store: (-store.same_cart.coverage, store.optimal_cart.total)
        )
        return built

    def _store_cart(
        self,
        *,
        matched: list[MatchedLine],
        items: dict[int, Item],
        quantities: dict[int, Decimal],
        store_prices: dict[int, Decimal],
        swap_options: list,
        record: NearbyRecord | None,
        chain_id: str,
        chain_name: str,
        store_id: str | None,
        chain_level: bool,
    ) -> NearbyStore:
        same_lines: list[CartLine] = []
        same_total = Decimal(0)
        unavailable = 0
        #: What this store actually sells per line, for the swap baseline: a
        #: swap must beat the price the cart already shows, not the primary
        #: product's price at some store that keys the item differently.
        readings: dict[int, tuple[CatalogProduct, Decimal]] = {}

        for line in matched:
            item = items.get(line.position)
            quantity = quantities.get(line.position, Decimal(1))
            unit = normalize_unit(item.unit if item else None)
            reading = _cheapest_reading(line, store_prices)

            if reading is None:
                unavailable += 1
                same_lines.append(
                    CartLine(
                        position=line.position,
                        barcode=str(line.product.barcode),
                        name=line.product.name or line.receipt_name,
                        qty=float(quantity),
                        unit=unit,
                        unit_price=None,
                        line_total=None,
                        available=False,
                        match_confidence=(
                            line.confidence if line.matched_by == "name" else None
                        ),
                    )
                )
                continue

            product, confidence, price = reading
            readings[line.position] = (product, price)
            line_total = price * quantity
            same_total += line_total
            same_lines.append(
                CartLine(
                    position=line.position,
                    barcode=str(product.barcode),
                    name=product.name or line.receipt_name,
                    qty=float(quantity),
                    unit=unit,
                    unit_price=_money(price),
                    line_total=_money(line_total),
                    available=True,
                    match_confidence=confidence,
                )
            )

        available = len(matched) - unavailable
        coverage = round(available / len(matched), 4) if matched else 0.0

        applied = choose_swaps(
            matched, quantities, store_prices, swap_options, readings=readings
        )
        optimal_lines, optimal_total, swaps = self._apply_swaps(
            matched=matched,
            items=items,
            quantities=quantities,
            store_prices=store_prices,
            same_lines=same_lines,
            applied=applied,
        )

        return NearbyStore(
            store_id=store_id or f"chain:{chain_id}",
            chain=chain_name,
            branch=(record.store.store_name if record else "") or chain_name,
            online=chain_level,
            location=(
                GeoPoint(lat=record.store.lat, lng=record.store.lng)
                if record is not None
                and record.store.located
                and record.store.lat is not None
                and record.store.lng is not None
                else None
            ),
            # A city-centre position cannot support a distance: quoting "1.2 km"
            # for a branch we only know the city of would be inventing precision.
            distance_m=(
                round(record.distance_m, 1)
                if record is not None and not record.store.approximate_location
                else None
            ),
            approximate_location=(
                record.store.approximate_location if record is not None else False
            ),
            # The price database publishes shelf prices, not delivery terms.
            delivery_fee=0.0,
            city=record.store.city if record else None,
            address=record.store.address if record else None,
            chain_level_estimate=chain_level,
            same_cart=Cart(
                items=same_lines,
                total=_money(same_total),
                unavailable_count=unavailable,
                coverage=coverage,
            ),
            optimal_cart=OptimalCart(
                items=optimal_lines,
                total=_money(optimal_total),
                unavailable_count=unavailable,
                coverage=coverage,
                swaps=swaps,
                savings_vs_same_cart=_money(same_total - optimal_total),
            ),
        )

    @staticmethod
    def _apply_swaps(
        *,
        matched: list[MatchedLine],
        items: dict[int, Item],
        quantities: dict[int, Decimal],
        store_prices: dict[int, Decimal],
        same_lines: list[CartLine],
        applied: dict[int, AppliedSwap],
    ) -> tuple[list[CartLine], Decimal, list[Swap]]:
        optimal_lines: list[CartLine] = []
        optimal_total = Decimal(0)
        swaps: list[Swap] = []

        for line, same in zip(matched, same_lines, strict=True):
            swap = applied.get(line.position)
            if swap is None:
                optimal_lines.append(same)
                if same.line_total is not None:
                    optimal_total += Decimal(str(same.line_total))
                continue

            item = items.get(line.position)
            unit = normalize_unit(item.unit if item else None)
            quantity = quantities.get(line.position, Decimal(1))
            line_total = swap.swapped_unit_price * quantity
            optimal_total += line_total
            optimal_lines.append(
                CartLine(
                    # A swap answers the same receipt line as the product it
                    # replaced, so the join key travels with it.
                    position=line.position,
                    barcode=str(swap.replacement.barcode),
                    name=swap.replacement.name,
                    qty=float(quantity),
                    unit=unit,
                    unit_price=_money(swap.swapped_unit_price),
                    line_total=_money(line_total),
                    available=True,
                    match_confidence=swap.similarity,
                )
            )
            swaps.append(
                Swap(
                    **{
                        "from": {
                            "barcode": str(swap.replaced.barcode),
                            "name": swap.replaced.name,
                            "unitPrice": _money(swap.original_unit_price),
                        }
                    },
                    to={
                        "barcode": str(swap.replacement.barcode),
                        "name": swap.replacement.name,
                        "unitPrice": _money(swap.swapped_unit_price),
                    },
                    qty=float(quantity),
                    unit=unit,
                    line_savings=_money(swap.line_savings),
                    reason="cheaper_similar",
                    similarity=swap.similarity,
                )
            )

        return optimal_lines, optimal_total, swaps

    # -- origin --------------------------------------------------------------

    def _origin(
        self,
        document: ReceiptDocument,
        here: tuple[float, float],
        items: dict[int, Item],
    ) -> NearbyStore | None:
        """The shop the receipt was bought at, priced at what was actually paid.

        Always returned when the receipt names a merchant, even if the branch
        cannot be placed on a map: "you paid this, here" is the baseline every
        other number on the screen is compared against.
        """
        merchant = document.receipt.merchant
        if not merchant.name and not merchant.branch_name:
            return None

        record = self._directory.resolve_origin(
            merchant.name, merchant.branch_name, here
        )
        paid_total = _decimal(document.receipt.totals.total)

        lines = [
            CartLine(
                position=item.position,
                barcode=str(item.code or ""),
                name=item.name,
                qty=float(_quantity(item)),
                unit=normalize_unit(item.unit),
                unit_price=_money(
                    _decimal(item.unit_price)
                    if item.unit_price
                    else _decimal(item.final_total) / _quantity(item)
                ),
                line_total=_money(_decimal(item.final_total)),
                available=True,
            )
            for item in items.values()
        ]
        cart = Cart(
            items=lines,
            total=_money(paid_total),
            unavailable_count=0,
            coverage=1.0,
        )
        located = (
            record is not None
            and record.store.located
            and record.store.lat is not None
            and record.store.lng is not None
        )
        return NearbyStore(
            store_id=record.store.store_id if record else "origin",
            chain=(record.store.chain_name if record else None)
            or merchant.name
            or "החנות שלכם",
            branch=(record.store.store_name if record else None)
            or merchant.branch_name
            or "",
            online=False,
            location=(
                GeoPoint(lat=record.store.lat, lng=record.store.lng)
                if located and record is not None
                else None
            ),
            distance_m=(
                round(distance_meters(here, (record.store.lat, record.store.lng)), 1)
                if located and record is not None
                else None
            ),
            delivery_fee=0.0,
            city=record.store.city if record else None,
            address=record.store.address if record else None,
            same_cart=cart,
            optimal_cart=OptimalCart(
                items=lines,
                total=cart.total,
                unavailable_count=0,
                coverage=1.0,
                swaps=[],
                savings_vs_same_cart=0.0,
            ),
        )

    # -- warnings ------------------------------------------------------------

    @staticmethod
    def _quality_warnings(
        document: ReceiptDocument,
        matched: list[MatchedLine],
        unmatched: list[UnmatchedLine],
        stores: list[NearbyStore],
        *,
        simulated: bool = False,
    ) -> list[str]:
        warnings: list[str] = []

        for line in matched:
            if (
                line.matched_by == "name"
                and line.confidence < CONFIDENT_NAME_MATCH_SCORE
            ):
                warnings.append(
                    f"uncertain: receipt.items[{line.position}] "
                    f"{line.receipt_name!r} was priced as {line.product.name!r} "
                    f"on a name match scoring {line.confidence:.2f}"
                )

        unreachable = sum(
            1 for line in unmatched if "could not be reached" in line.reason
        )
        if unreachable:
            warnings.append(
                f"{unreachable} of {len(document.receipt.items)} receipt lines "
                "could not be checked at all because the price database did not "
                "respond; this is an outage, not a verdict on those products"
            )

        if unmatched:
            # A simulated cart is built from the receipt itself, so it contains
            # every line whether or not the catalogue knew it. Claiming they
            # were excluded would contradict the totals on the same screen.
            consequence = (
                "; the simulated totals price them from the receipt instead"
                if simulated
                else " and are excluded from every cart total"
            )
            warnings.append(
                f"{len(unmatched)} of {len(document.receipt.items)} receipt lines "
                f"could not be matched to the price database{consequence}"
            )
        if stores and not any(store.same_cart.coverage >= 1.0 for store in stores):
            warnings.append(
                "no store nearby carries every matched product; carts are ranked "
                "by how much of the cart they cover before price"
            )
        if any(store.chain_level_estimate for store in stores):
            warnings.append(
                "some totals are chain-level estimates because the price database "
                "returned no per-store breakdown"
            )
        return warnings


_SERVICE: NearbyService | None = None
_SERVICE_LOCK = threading.Lock()


def default_service() -> NearbyService:
    """The process-wide pricer, so its catalogue's pool and caches survive."""
    global _SERVICE
    with _SERVICE_LOCK:
        if _SERVICE is None:
            _SERVICE = NearbyService()
        return _SERVICE


__all__ = ["NearbyService", "default_service"]
