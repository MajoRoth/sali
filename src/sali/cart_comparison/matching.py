"""Resolve receipt lines to products in the price database.

Barcode first: a receipt that prints a 12-14 digit code names the exact product,
and the catalogue is keyed on that code, so the match is free and certain.

Name second: weighed goods (produce, deli, bakery) carry a merchant-internal PLU
instead, which means nothing outside that chain. Those lines are searched by
name, and because a wrong match silently corrupts a store's cart total, a
candidate is only accepted above a confidence floor.
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from sali.cart_comparison.catalog import ProductLookup, SupermarketsCatalog
from sali.cart_comparison.configuration import (
    BARCODE_LENGTHS,
    BARCODE_LOOKUP_WORKERS,
    MIN_NAME_MATCH_SCORE,
)
from sali.cart_comparison.models import CatalogProduct, MatchMethod
from sali.receipt_extraction.models import Item

#: Characters Hebrew receipts use decoratively around abbreviations. Stripping
#: them lets `חלב תנובה 3%` and `חלב תנובה 3 %` tokenize alike.
_PUNCTUATION = re.compile(r"[\"'`׳״.,;:!?()\[\]{}/\\|*+\-–—_=<>@#&~^$₪%]+")
_WHITESPACE = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Fold a product name to comparable tokens separated by single spaces."""
    folded = _PUNCTUATION.sub(" ", text.strip().casefold())
    return _WHITESPACE.sub(" ", folded).strip()


def tokenize(text: str) -> list[str]:
    return [token for token in normalize(text).split(" ") if token]


def is_barcode(code: str | None) -> bool:
    """Whether a receipt's printed code is a catalogue barcode."""
    return bool(code) and code.isdigit() and len(code) in BARCODE_LENGTHS


def _tokens_match(left: str, right: str) -> bool:
    """Whether two tokens name the same thing.

    Receipts truncate words to fit a narrow printer — `שוקולד` becomes `שוקול` —
    so a prefix of three characters or more counts, which is short enough to
    survive truncation and long enough not to collide across Hebrew roots.
    """
    if left == right:
        return True
    shorter, longer = (left, right) if len(left) <= len(right) else (right, left)
    return len(shorter) >= 3 and longer.startswith(shorter)


#: Applied when both names state a pack size and none of the sizes agree.
#: `ממרח נוטלה 350 גרם` against `ממרח נוטלה 400 גרם` is the same product in the
#: wrong jar, and pricing the cart against the wrong jar is a silent error.
_SIZE_CONFLICT_FACTOR = 0.6


def _numbers(tokens: list[str]) -> set[str]:
    return {token for token in tokens if any(char.isdigit() for char in token)}


def similarity(receipt_name: str, product_name: str) -> float:
    """Dice coefficient over matched tokens, in 0.0-1.0.

    Symmetric on purpose: a candidate that contains every receipt word but
    twenty more of its own is a worse match than one that contains exactly the
    receipt's words, and only a symmetric score expresses that.
    """
    receipt_tokens = tokenize(receipt_name)
    product_tokens = tokenize(product_name)
    if not receipt_tokens or not product_tokens:
        return 0.0

    unclaimed = list(product_tokens)
    matched = 0
    for token in receipt_tokens:
        for index, candidate in enumerate(unclaimed):
            if _tokens_match(token, candidate):
                matched += 1
                unclaimed.pop(index)
                break

    score = (2 * matched) / (len(receipt_tokens) + len(product_tokens))

    receipt_numbers = _numbers(receipt_tokens)
    product_numbers = _numbers(product_tokens)
    if (
        receipt_numbers
        and product_numbers
        and receipt_numbers.isdisjoint(product_numbers)
    ):
        score *= _SIZE_CONFLICT_FACTOR

    return score


def _to_product(raw: dict[str, Any]) -> CatalogProduct | None:
    """Read a catalogue row, refusing the ones that cannot be priced.

    Two id shapes are in play and both are legitimate. The hosted service keys
    products on opaque cuids (`cmlftahii00v7gdqvf17rt2bw`); the open instance
    uses the barcode as the id. Only `productBarcode` is validated, because
    that is what identifies the product across stores — the id is an opaque
    handle to pass back to `compare-prices`, and demanding it look like a
    number rejects the entire hosted catalogue.

    A barcode of 0 is the real failure: around one row in eight comes back with
    a float-formatted name and `productBarcode: 0`, and since they all share
    that barcode, admitting two would silently merge two different products
    into one line of the cart.
    """
    identifier = raw.get("id")
    barcode = raw.get("productBarcode")
    if not isinstance(identifier, str) or not identifier:
        return None
    if not isinstance(barcode, int) or isinstance(barcode, bool) or barcode <= 0:
        return None
    manufacturer = raw.get("manufacturerOrImporterName")
    return CatalogProduct(
        product_id=identifier,
        barcode=barcode,
        name=str(raw.get("productName") or ""),
        manufacturer=str(manufacturer) if manufacturer else None,
    )


@dataclass(frozen=True)
class LineMatch:
    """The outcome of resolving one receipt line."""

    product: CatalogProduct | None
    matched_by: MatchMethod | None
    confidence: float
    reason: str | None


class CartMatcher:
    """Match receipt lines against the catalogue, barcode first."""

    def __init__(
        self,
        catalog: SupermarketsCatalog,
        *,
        minimum_score: float = MIN_NAME_MATCH_SCORE,
    ) -> None:
        self._catalog = catalog
        self._minimum_score = minimum_score

    def match(self, item: Item) -> LineMatch:
        if is_barcode(item.code):
            return self._from_barcode(item.code or "")
        return self._match_by_name(item.name)

    def match_all(self, items: list[Item]) -> list[LineMatch]:
        """Resolve a whole receipt, in the order it was given.

        Every line costs at least one call to a catalogue that answers in
        seconds, so a fifty-line receipt resolved one line after another takes
        minutes — long enough that the shopper assumes the app has hung.
        Resolving them concurrently is what makes the request interactive; the
        worker cap keeps it from looking like an attack on a free service.
        """
        if len(items) < 2:
            return [self.match(item) for item in items]

        with ThreadPoolExecutor(
            max_workers=min(BARCODE_LOOKUP_WORKERS, len(items))
        ) as pool:
            return list(pool.map(self.match, items))

    def _from_barcode(self, barcode: str) -> LineMatch:
        found = self._lookup(barcode)
        if found.product is not None:
            product = _to_product(found.product)
            if product is not None:
                return LineMatch(product, "barcode", 1.0, None)

        if not found.answered:
            # We never got to ask. Reporting this as "not in the price database"
            # would be a claim about the shopper's shopping, made on the basis
            # of somebody else's outage.
            return LineMatch(
                None,
                None,
                0.0,
                f"the price database could not be reached to look up {barcode}",
            )

        # A printed barcode the catalogue does not know is a real gap, not a
        # reason to guess by name: the name is usually the merchant's own
        # abbreviation of a product the database simply does not carry.
        return LineMatch(
            None,
            None,
            0.0,
            f"barcode {barcode} is not in the price database",
        )

    def _lookup(self, barcode: str) -> ProductLookup:
        """Ask the catalogue, tolerating a client that cannot say if it answered."""
        finder = getattr(self._catalog, "find_product", None)
        if finder is None:
            return ProductLookup(self._catalog.product_by_barcode(barcode), True)
        return finder(barcode)

    def _match_by_name(self, name: str) -> LineMatch:
        candidates = self._candidates(name)
        if not candidates:
            return LineMatch(None, None, 0.0, "no catalogue product matched the name")

        best_product: CatalogProduct | None = None
        best_score = 0.0
        for raw in candidates:
            product = _to_product(raw)
            if product is None:
                continue
            score = similarity(name, product.name)
            if score > best_score:
                best_product, best_score = product, score

        if best_product is None or best_score < self._minimum_score:
            return LineMatch(
                None,
                None,
                best_score,
                f"best name match scored {best_score:.2f}, below the "
                f"{self._minimum_score:.2f} confidence floor",
            )
        return LineMatch(best_product, "name", best_score, None)

    def _candidates(self, name: str) -> list[dict[str, Any]]:
        """Search the catalogue for anything plausibly this line.

        Search is a substring match over product names, so the full receipt name
        is tried first for precision and individual words only as a fallback:
        a bare word like `חלב` matches thousands of rows.
        """
        seen: set[str] = set()
        candidates: list[dict[str, Any]] = []

        for query in self._queries(name):
            for raw in self._catalog.search_products(query):
                identifier = raw.get("id")
                if isinstance(identifier, str) and identifier not in seen:
                    seen.add(identifier)
                    candidates.append(raw)
            if candidates:
                break
        return candidates

    @staticmethod
    def _queries(name: str) -> list[str]:
        normalized = normalize(name)
        tokens = [token for token in normalized.split(" ") if len(token) >= 3]
        queries = [normalized]
        # Longest words carry the most meaning, and a receipt's trailing tokens
        # are usually size or packaging noise.
        queries.extend(sorted(tokens, key=len, reverse=True)[:2])
        return list(dict.fromkeys(query for query in queries if query))


__all__ = [
    "CartMatcher",
    "LineMatch",
    "is_barcode",
    "normalize",
    "similarity",
    "tokenize",
]
