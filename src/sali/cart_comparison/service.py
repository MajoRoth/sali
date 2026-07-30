"""Compare an extracted receipt's cart across stores.

This is the join between the two APIs: a Receipt Document names what was bought
in the merchant's own words, and the price database names what things cost in
catalogue terms. Everything here is about surviving the gap between the two —
lines that cannot be matched are reported rather than dropped, and a cart is
still returned when the price database has nothing to say, because "no store
could be priced" is an answer a shopper can act on and a silent empty list is
not.
"""

from __future__ import annotations

from sali.cart_comparison.catalog import SupermarketsCatalog
from sali.cart_comparison.configuration import CONFIDENT_NAME_MATCH_SCORE
from sali.cart_comparison.matching import CartMatcher
from sali.cart_comparison.models import (
    CartComparison,
    MatchedLine,
    UnmatchedLine,
)
from sali.cart_comparison.pricing import read_store_prices
from sali.cart_comparison.ranking import rank_carts, store_directory
from sali.receipt_extraction.models import ReceiptDocument


class CartComparisonService:
    """Match a Receipt Document to the catalogue and rank stores by cart price."""

    def __init__(
        self,
        catalog: SupermarketsCatalog | None = None,
        matcher: CartMatcher | None = None,
    ) -> None:
        self._catalog = catalog or SupermarketsCatalog()
        self._matcher = matcher or CartMatcher(self._catalog)

    def compare(
        self,
        document: ReceiptDocument,
        *,
        city: str | None = None,
    ) -> CartComparison:
        matched, unmatched = self._resolve(document)
        warnings: list[str] = []

        prices = []
        if matched:
            product_ids = list(
                dict.fromkeys(line.product.product_id for line in matched)
            )
            prices = read_store_prices(self._catalog.compare_prices(product_ids))

        if matched and not prices:
            warnings.append(
                "no store prices: the price database has no current listings for "
                "any matched product"
            )

        stores = store_directory(self._catalog.stores(city=city) if city else [])
        complete, partial = rank_carts(matched, prices, stores=stores, city=city)

        uncertain = [
            line
            for line in matched
            if line.matched_by == "name"
            and line.confidence < CONFIDENT_NAME_MATCH_SCORE
        ]
        for line in uncertain:
            warnings.append(
                f"uncertain: receipt.items[{line.position}] "
                f"{line.receipt_name!r} was priced as {line.product.name!r} "
                f"on a name match scoring {line.confidence:.2f}"
            )

        if unmatched:
            warnings.append(
                f"{len(unmatched)} of {len(document.receipt.items)} receipt lines "
                "could not be matched to the price database and are excluded from "
                "every cart total"
            )
        if not complete and partial:
            warnings.append(
                "no store carries every matched product; partial carts are ranked "
                "by how much of the cart they cover"
            )
        if any(cart.chain_level_estimate for cart in complete + partial):
            warnings.append(
                "some totals are chain-level estimates because the price database "
                "returned no per-store breakdown"
            )

        return CartComparison(
            currency=document.receipt.transaction.currency,
            receipt_total=document.receipt.totals.total,
            matched=matched,
            unmatched=unmatched,
            complete_carts=complete,
            partial_carts=partial,
            warnings=warnings,
        )

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
                )
            )

        return matched, unmatched


__all__ = ["CartComparisonService"]
