"""Correct LLM misreadings in an extracted receipt against the catalogue.

The extractor reads a photographed receipt almost right: a barcode with one
digit swapped, a name with a word truncated by the printer. Almost right is
still wrong downstream — the swapped digit prices as "not in the database"
and the line goes unmatched. `/products/ocr-match` was built for exactly this
input: it returns the catalogue products nearest a noisy (code, name, price)
reading, and this pass rewrites the item to the catalogue's version of itself
when the match is near enough to be beyond reasonable doubt.

The endpoint ranks but does not judge: it always fills its limit, however bad
the fit, and reports no distance. Acceptance is therefore decided here, with
the same name-similarity score the cart matcher trusts — plus one extra path
for a printed code within a misread digit or two of a candidate's barcode,
which is the error this pass exists for.

Correction improves a document, it never makes one — so any catalogue trouble
returns the document exactly as extracted, and every rewrite is recorded in
the document's warnings the way reconciliation records its own.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from sali.cart_comparison.catalog import SupermarketsCatalog, default_catalog
from sali.cart_comparison.configuration import (
    BARCODE_LOOKUP_WORKERS,
    MIN_NAME_MATCH_SCORE,
    OCR_CODE_EDIT_DISTANCE,
    OCR_CORRECTION_MIN_SCORE,
)
from sali.cart_comparison.matching import is_barcode, similarity, to_product
from sali.cart_comparison.models import CatalogProduct
from sali.receipt_extraction.models import Item, ReceiptDocument

logger = logging.getLogger(__name__)


def _edit_distance(left: str, right: str) -> int:
    """Levenshtein distance, for codes short enough that O(n*m) is free."""
    if left == right:
        return 0
    previous = list(range(len(right) + 1))
    for row, left_char in enumerate(left, start=1):
        current = [row]
        for column, right_char in enumerate(right, start=1):
            current.append(
                min(
                    previous[column] + 1,
                    current[column - 1] + 1,
                    previous[column - 1] + (left_char != right_char),
                )
            )
        previous = current
    return previous[-1]


def _price_for(item: Item) -> float:
    """The per-unit price, the axis the endpoint compares store prices on."""
    return float(item.unit_price or item.final_total)


class OcrReceiptCorrector:
    """Rewrite misread item codes and names to their catalogue versions."""

    def __init__(
        self,
        catalog: SupermarketsCatalog | None = None,
        *,
        minimum_score: float = OCR_CORRECTION_MIN_SCORE,
    ) -> None:
        self._catalog = catalog or default_catalog()
        self._minimum_score = minimum_score

    def correct(self, document: ReceiptDocument) -> ReceiptDocument:
        """The document with items the catalogue recognises, or as given.

        Never raises: extraction has already succeeded, and a correction pass
        able to fail it would turn catalogue downtime into "your receipt could
        not be read" — a falsehood about the receipt.
        """
        items = document.receipt.items
        if not items:
            return document
        try:
            outcomes = self._correct_all(items)
        except Exception:  # correction improves a document, never breaks one
            logger.warning("receipt correction abandoned", exc_info=True)
            return document

        warnings = [warning for _, notes in outcomes for warning in notes]
        if not warnings:
            return document
        receipt = document.receipt.model_copy(
            update={"items": [item for item, _ in outcomes]}
        )
        return document.model_copy(
            update={
                "receipt": receipt,
                "warnings": [*document.warnings, *warnings],
            }
        )

    def _correct_all(self, items: list[Item]) -> list[tuple[Item, list[str]]]:
        """Every line costs a slow catalogue call, so lines run concurrently."""
        if len(items) < 2:
            return [self._correct_item(item) for item in items]
        with ThreadPoolExecutor(
            max_workers=min(BARCODE_LOOKUP_WORKERS, len(items))
        ) as pool:
            return list(pool.map(self._correct_item, items))

    def _correct_item(self, item: Item) -> tuple[Item, list[str]]:
        if self._already_catalogued(item):
            return item, []
        best, score = self._nearest(item)
        if best is None or not self._accepted(item, best, score):
            return item, []

        path = f"receipt.items[{item.position}]"
        updates: dict[str, str] = {}
        warnings: list[str] = []
        code = str(best.barcode)
        if item.code != code:
            updates["code"] = code
            warnings.append(f"corrected: {path}.code to its catalogue barcode")
        if item.name != best.name:
            updates["name"] = best.name
            warnings.append(f"corrected: {path}.name to its catalogue name")
        if not updates:
            return item, []
        return item.model_copy(update=updates), warnings

    def _already_catalogued(self, item: Item) -> bool:
        """Whether the printed code already names a real catalogue product.

        A hit means the extractor read the barcode right, and right beats any
        nearest-neighbour guess. No answer also ends the line's correction:
        with the catalogue silent there is no ground for overruling what is
        printed on the receipt.
        """
        if not is_barcode(item.code):
            return False
        lookup = self._catalog.find_product(item.code or "")
        if not lookup.answered:
            return True
        return lookup.product is not None and to_product(lookup.product) is not None

    def _nearest(self, item: Item) -> tuple[CatalogProduct | None, float]:
        candidates = self._catalog.ocr_match(
            item.code or "", item.name, _price_for(item)
        )
        best: CatalogProduct | None = None
        best_score = 0.0
        for raw in candidates:
            product = to_product(raw)
            if product is None:
                continue
            score = similarity(item.name, product.name)
            if best is None or score > best_score:
                best, best_score = product, score
        return best, best_score

    def _accepted(self, item: Item, product: CatalogProduct, score: float) -> bool:
        """Whether a candidate is beyond reasonable doubt.

        A wrong rewrite is worse than none — it is saved with the receipt and
        re-priced on every open — so the name must clear the bar a missing
        barcode clears in matching, unless the printed code is within a
        misread digit or two of the candidate's barcode, in which case the
        code corroborates what the name alone could not prove.
        """
        if score >= self._minimum_score:
            return True
        code = item.code or ""
        return (
            score >= MIN_NAME_MATCH_SCORE
            and code.isdigit()
            and _edit_distance(code, str(product.barcode)) <= OCR_CODE_EDIT_DISTANCE
        )


__all__ = ["OcrReceiptCorrector"]
