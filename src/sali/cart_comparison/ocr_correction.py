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
    BARCODE_LENGTHS,
    BARCODE_LOOKUP_WORKERS,
    LOCAL_CODE_NAME_SCORE,
    LOCAL_SEARCH_CANDIDATE_LIMIT,
    MIN_NAME_MATCH_SCORE,
    OCR_CODE_EDIT_DISTANCE,
    OCR_CORRECTION_MIN_SCORE,
)
from sali.cart_comparison.matching import (
    has_valid_gtin_checksum,
    is_barcode,
    is_local_code,
    local_similarity,
    similarity,
    to_product,
    tokenize,
)
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
        exact, conclusive = self._exact_catalogue_product(item)
        if exact is not None:
            return self._rewrite(item, exact, replace_code=False)
        if conclusive:
            # The code identifies a catalogue row, but that row has no usable
            # canonical name.  Fuzzy matching cannot improve the identity and
            # only adds a slow, ambiguous network round-trip.
            return item, []

        recovered = self._recover_invalid_gtin(item)
        if recovered is not None:
            return self._rewrite(item, recovered, replace_code=True)

        best, score = self._nearest(item)
        if best is None or not self._accepted(item, best, score):
            return item, []

        return self._rewrite(item, best, replace_code=True)

    @staticmethod
    def _rewrite(
        item: Item,
        product: CatalogProduct,
        *,
        replace_code: bool,
    ) -> tuple[Item, list[str]]:
        """Apply a catalogue reading without touching receipt arithmetic."""

        path = f"receipt.items[{item.position}]"
        updates: dict[str, str] = {}
        warnings: list[str] = []
        code = str(product.barcode)
        if replace_code and item.code != code:
            updates["code"] = code
            warnings.append(f"corrected: {path}.code to its catalogue barcode")
        if item.name != product.name:
            updates["name"] = product.name
            warnings.append(f"corrected: {path}.name to its catalogue name")
        if not updates:
            return item, []
        return item.model_copy(update=updates), warnings

    def _exact_catalogue_product(
        self, item: Item
    ) -> tuple[CatalogProduct | None, bool]:
        """Return a safe exact-code name and whether the lookup is conclusive.

        A global barcode is the product identity, so an exact catalogue hit is
        authoritative even when the visual OCR name is badly damaged.  A local
        SKU is not globally unique and is accepted only when its name provides
        independent support.  ``conclusive`` is true for an exact global row
        with a blank catalogue name: it can still be priced by code, but there
        is no honest replacement text and no reason to wait on fuzzy matching.
        """
        code = item.code or ""
        global_barcode = is_barcode(code)
        local_code = is_local_code(code)
        if not global_barcode and not local_code:
            return None, False

        lookup = self._catalog.find_product(item.code or "")
        if not lookup.answered:
            # `/products/ocr-match` has its own health circuit.  One failed
            # exact lookup must not suppress evidence from that endpoint.
            return None, False
        if lookup.product is None:
            return None, False

        product = to_product(lookup.product)
        if product is None or str(product.barcode) != str(int(code)):
            return None, False
        if global_barcode:
            return (product, True) if product.name.strip() else (None, True)
        if (
            product.name.strip()
            and local_similarity(item.name, product.name) >= LOCAL_CODE_NAME_SCORE
        ):
            return product, True
        return None, False

    def _recover_invalid_gtin(self, item: Item) -> CatalogProduct | None:
        """Recover a shifted/misread GTIN through fast name-token search.

        The hosted OCR-match endpoint is both slow and frequently unavailable.
        A common visual error is more structured than a general fuzzy match:
        the model drops one digit and duplicates another, producing an invalid
        check digit while leaving the real GTIN within two edits.  Search the
        catalogue by each visible word concurrently, then accept only a unique
        checksum-valid candidate at the smallest edit distance.  This is
        stricter than a name-only rewrite and turned the supplied receipt's
        shifted barcode into a three-second lookup instead of a timeout.
        """
        code = item.code or ""
        if (
            not code.isdigit()
            or len(code) not in BARCODE_LENGTHS
            or has_valid_gtin_checksum(code)
        ):
            return None

        search = getattr(self._catalog, "search_products", None)
        if not callable(search):
            return None
        queries = list(
            dict.fromkeys(
                token
                for token in tokenize(item.name)
                if len(token) >= 3 and not any(char.isdigit() for char in token)
            )
        )[:4]
        if not queries:
            return None

        def find(query: str) -> list[dict[str, object]]:
            try:
                return search(query, limit=LOCAL_SEARCH_CANDIDATE_LIMIT)
            except Exception:
                logger.warning("catalogue token search failed", exc_info=True)
                return []

        if len(queries) == 1:
            batches = [find(queries[0])]
        else:
            with ThreadPoolExecutor(max_workers=len(queries)) as pool:
                batches = list(pool.map(find, queries))

        by_barcode: dict[int, tuple[CatalogProduct, int, float]] = {}
        for raw in (raw for batch in batches for raw in batch):
            product = to_product(raw)
            candidate_code = str(product.barcode) if product is not None else ""
            if (
                product is None
                or not product.name.strip()
                or len(candidate_code) != len(code)
                or not has_valid_gtin_checksum(candidate_code)
            ):
                continue
            distance = _edit_distance(code, candidate_code)
            score = similarity(item.name, product.name)
            if distance > OCR_CODE_EDIT_DISTANCE or score <= 0:
                continue
            current = by_barcode.get(product.barcode)
            if current is None or (distance, -score) < (current[1], -current[2]):
                by_barcode[product.barcode] = (product, distance, score)

        ranked = sorted(by_barcode.values(), key=lambda found: (found[1], -found[2]))
        if not ranked:
            return None
        # Two different products equally close to a broken code are ambiguous;
        # leave the line for the conservative general matcher.
        if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
            return None
        return ranked[0][0]

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
