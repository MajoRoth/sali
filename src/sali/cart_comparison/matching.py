"""Resolve receipt lines to products in the price database.

Barcode first: a receipt that prints a 12-14 digit code names the exact product,
and the catalogue is keyed on that code, so the match is free and certain. A
printed barcode the catalogue lacks — usually a store brand — falls back to the
name, but at a floor high enough that only a near-certain reading is accepted.

Name second: weighed goods (produce, deli, bakery) carry a merchant-internal PLU
instead, which means nothing outside that chain. Those lines are searched by
name, and because a wrong match silently corrupts a store's cart total, a
candidate is only accepted above a confidence floor.

A name match also keeps its *alternates*: other catalogue products that read the
receipt text just as well. Chains key identical produce on their own internal
codes, so without alternates a matched banana can only ever be priced inside one
chain and every other store shows it as missing.
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

from sali.cart_comparison.catalog import ProductLookup, SupermarketsCatalog
from sali.cart_comparison.configuration import (
    ALTERNATE_MATCH_LIMIT,
    BARCODE_LENGTHS,
    BARCODE_LOOKUP_WORKERS,
    BARCODE_MISS_NAME_SCORE,
    CONFIDENT_NAME_MATCH_SCORE,
    MIN_NAME_MATCH_SCORE,
)
from sali.cart_comparison.models import AlternateProduct, CatalogProduct, MatchMethod
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


#: A numeric id, possibly float-formatted (`7290000074184.0`). The digits are
#: the product's real code, exported through a float column upstream.
_NUMERIC_ID = re.compile(r"^(\d+)(?:\.0+)?$")


def _recovered_barcode(identifier: str) -> int | None:
    """The barcode a broken row's id encodes, if it encodes one."""
    matched = _NUMERIC_ID.match(identifier)
    if matched is None:
        return None
    value = int(matched.group(1))
    return value if value > 0 else None


def to_product(raw: dict[str, Any]) -> CatalogProduct | None:
    """Read a catalogue row, refusing the ones that cannot be priced.

    Two id shapes are in play and both are legitimate. The hosted service keys
    products on opaque cuids (`cmlftahii00v7gdqvf17rt2bw`); the open instance
    uses the barcode as the id. Only `productBarcode` is validated, because
    that is what identifies the product across stores — the id is an opaque
    handle to pass back to `compare-prices`, and demanding it look like a
    number rejects the entire hosted catalogue.

    Around one row in eight arrives broken — `productBarcode: 0` and a
    float-formatted id like `7290000074184.0`. Admitting those as they stand
    would merge every such product into one barcode-0 cart line, but the id's
    digits *are* the real barcode, exported through a float column. Recovered,
    the row prices normally — and against the clean id the price database
    answers with its full cross-chain comparison, where the broken id got the
    barcode-0 remnant.
    """
    identifier = raw.get("id")
    barcode = raw.get("productBarcode")
    if not isinstance(identifier, str) or not identifier:
        return None
    if not isinstance(barcode, int) or isinstance(barcode, bool) or barcode <= 0:
        recovered = _recovered_barcode(identifier)
        if recovered is None:
            return None
        barcode = recovered
        identifier = str(recovered)
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
    #: Other products that read the line as well as `product` does, so a store
    #: stocking the same thing under a different code can still price it.
    alternates: tuple[AlternateProduct, ...] = field(default=())


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
            return self._from_barcode(item.code or "", item.name)
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

    def _from_barcode(self, barcode: str, name: str) -> LineMatch:
        found = self._lookup(barcode)
        if found.product is not None:
            product = to_product(found.product)
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

        # A barcode the catalogue lacks is usually a store brand — the exact
        # product genuinely is not there, but its line still names what it is,
        # and another maker's identical פתי בר can be. The name is trusted only
        # at a floor high enough to exclude lookalikes; anything less certain is
        # reported as the barcode gap it is.
        fallback = self._match_by_name(name, minimum_score=BARCODE_MISS_NAME_SCORE)
        if fallback.product is not None:
            return fallback

        return LineMatch(
            None,
            None,
            fallback.confidence,
            f"barcode {barcode} is not in the price database",
        )

    def _lookup(self, barcode: str) -> ProductLookup:
        """Ask the catalogue, tolerating a client that cannot say if it answered."""
        finder = getattr(self._catalog, "find_product", None)
        if finder is None:
            return ProductLookup(self._catalog.product_by_barcode(barcode), True)
        return finder(barcode)

    def _match_by_name(
        self,
        name: str,
        *,
        minimum_score: float | None = None,
    ) -> LineMatch:
        floor = self._minimum_score if minimum_score is None else minimum_score
        candidates = self._candidates(name)
        if not candidates:
            return LineMatch(None, None, 0.0, "no catalogue product matched the name")

        # Best score per barcode: two rows sharing a barcode are one product,
        # and letting both through would price the same thing against itself.
        scored: dict[int, tuple[CatalogProduct, float]] = {}
        for raw in candidates:
            product = to_product(raw)
            if product is None:
                continue
            score = similarity(name, product.name)
            current = scored.get(product.barcode)
            if current is None or score > current[1]:
                scored[product.barcode] = (product, score)

        ranked = sorted(scored.values(), key=lambda pair: pair[1], reverse=True)
        best_score = ranked[0][1] if ranked else 0.0
        if not ranked or best_score < floor:
            return LineMatch(
                None,
                None,
                best_score,
                f"best name match scored {best_score:.2f}, below the "
                f"{floor:.2f} confidence floor",
            )

        # An alternate must be as good a reading as the winner, or confident
        # enough to have needed no second look on its own. Anything looser
        # would quietly price a different product at some other store.
        alternates = tuple(
            AlternateProduct(product=product, confidence=round(score, 3))
            for product, score in ranked[1 : ALTERNATE_MATCH_LIMIT + 1]
            if score >= best_score - 1e-9
            or score >= max(CONFIDENT_NAME_MATCH_SCORE, floor)
        )
        return LineMatch(ranked[0][0], "name", best_score, None, alternates)

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
    "to_product",
    "tokenize",
]
