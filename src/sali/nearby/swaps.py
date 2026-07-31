"""The optimal cart: the same shop, done cheaper, without changing what you eat.

A swap is only worth showing if the shopper would actually accept it, so the bar
is high and deliberately conservative. Two products are interchangeable here only
when their names agree strongly — which, because the similarity score penalises
disagreeing numbers, already rejects the 400 g jar standing in for the 350 g one.
Everything else stays exactly as bought: a cart where half the lines silently
became a different brand is not the shopper's cart, and the headline saving it
produces is a lie.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from sali.cart_comparison.catalog import SupermarketsCatalog
from sali.cart_comparison.configuration import (
    SWAP_SEARCH_LINES,
    SWAP_SEARCH_WORKERS,
)
from sali.cart_comparison.matching import similarity, to_product
from sali.cart_comparison.models import CatalogProduct, MatchedLine

#: Name agreement below which two products are not the same thing. Set high on
#: purpose: an unwanted substitution costs more trust than a shekel saves.
SWAP_SIMILARITY_FLOOR = 0.62

#: Alternatives considered per cart line. The catalogue search returns its rows
#: name-ordered rather than by relevance, so a wider net mostly buys noise.
CANDIDATES_PER_LINE = 8

#: A swap has to be worth the shopper's attention. Below this it is rounding.
MIN_SWAP_SAVING = Decimal("0.05")


@dataclass(frozen=True)
class SwapOption:
    """A product that could stand in for one cart line."""

    position: int
    product: CatalogProduct
    similarity: float


def _candidates_for(
    catalog: SupermarketsCatalog,
    line: MatchedLine,
    per_line: int,
) -> list[SwapOption]:
    query = line.product.name.strip() or line.receipt_name
    if not query:
        return []

    scored: list[SwapOption] = []
    for raw in catalog.search_products(query):
        product = to_product(raw)
        if product is None or product.barcode == line.product.barcode:
            continue
        score = similarity(line.product.name, product.name)
        if score < SWAP_SIMILARITY_FLOOR:
            continue
        scored.append(
            SwapOption(
                position=line.position,
                product=product,
                similarity=round(score, 3),
            )
        )

    scored.sort(key=lambda option: option.similarity, reverse=True)
    return scored[:per_line]


def _paid(line: MatchedLine) -> Decimal:
    """What the line cost, as a number.

    `paid` is the receipt's own string. Sorting the strings looked the same in
    review and quietly sent the swap-search budget to the lexicographically
    largest lines — "9.90" outranking "69.00" — which is precisely the cheap
    tail the search is supposed to skip.
    """
    try:
        return Decimal(line.paid)
    except InvalidOperation:
        return Decimal(0)


def find_candidates(
    catalog: SupermarketsCatalog,
    matched: list[MatchedLine],
    *,
    per_line: int = CANDIDATES_PER_LINE,
    max_lines: int = SWAP_SEARCH_LINES,
) -> list[SwapOption]:
    """Search the catalogue for products that could replace each cart line.

    Searched by the catalogue's own name for the matched product rather than the
    receipt's abbreviation: the receipt says `קוטג 5%`, the catalogue says
    `קוטג' 5% 250 גרם`, and only the second finds its own shelf-mates.

    Only the cart's most expensive lines are searched, and they are searched
    concurrently. Each search is a slow call to the hosted catalogue, so
    searching all fifty lines of a receipt would cost more waiting than the
    whole feature is worth — and a swap on a ₪2 line cannot repay it. Ranking by
    what was paid puts the search where the savings are.
    """
    ranked = sorted(matched, key=_paid, reverse=True)[:max_lines]
    if not ranked:
        return []

    with ThreadPoolExecutor(max_workers=min(SWAP_SEARCH_WORKERS, len(ranked))) as pool:
        found = pool.map(lambda line: _candidates_for(catalog, line, per_line), ranked)

    options: list[SwapOption] = []
    for batch in found:
        options.extend(batch)
    return options


@dataclass(frozen=True)
class AppliedSwap:
    """A substitution chosen for one store, with what it saves there."""

    position: int
    replaced: CatalogProduct
    replacement: CatalogProduct
    original_unit_price: Decimal
    swapped_unit_price: Decimal
    quantity: Decimal
    similarity: float

    @property
    def line_savings(self) -> Decimal:
        return (self.original_unit_price - self.swapped_unit_price) * self.quantity


def choose_swaps(
    matched: list[MatchedLine],
    quantities: dict[int, Decimal],
    store_prices: dict[int, Decimal],
    options: list[SwapOption],
    *,
    readings: dict[int, tuple[CatalogProduct, Decimal]] | None = None,
) -> dict[int, AppliedSwap]:
    """Pick the best substitution per line, using one store's own prices.

    A candidate the store does not stock is not an option there, and a candidate
    it stocks at a higher price is not a saving — so this is evaluated per store
    rather than once for the cart.

    `readings` names what the store's cart actually shows for each line — which
    may be an alternate of the matched product, priced differently — so a swap
    is measured against the price on the cart, never against a product the
    store does not sell.
    """
    by_position: dict[int, list[SwapOption]] = {}
    for option in options:
        by_position.setdefault(option.position, []).append(option)

    chosen: dict[int, AppliedSwap] = {}
    for line in matched:
        if readings is not None:
            replaced, original = readings.get(line.position, (None, None))
        else:
            replaced, original = line.product, store_prices.get(line.product.barcode)
        if replaced is None or original is None:
            # The store cannot price what was actually bought, so there is no
            # baseline to beat and swapping would compare against nothing.
            continue

        quantity = quantities.get(line.position, Decimal(1))
        best: AppliedSwap | None = None
        for option in by_position.get(line.position, []):
            replacement_price = store_prices.get(option.product.barcode)
            if replacement_price is None or replacement_price >= original:
                continue
            candidate = AppliedSwap(
                position=line.position,
                replaced=replaced,
                replacement=option.product,
                original_unit_price=original,
                swapped_unit_price=replacement_price,
                quantity=quantity,
                similarity=option.similarity,
            )
            if candidate.line_savings < MIN_SWAP_SAVING:
                continue
            if best is None or candidate.line_savings > best.line_savings:
                best = candidate

        if best is not None:
            chosen[line.position] = best

    return chosen


__all__ = [
    "CANDIDATES_PER_LINE",
    "MIN_SWAP_SAVING",
    "SWAP_SIMILARITY_FLOOR",
    "AppliedSwap",
    "SwapOption",
    "choose_swaps",
    "find_candidates",
]
