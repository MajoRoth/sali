"""Matching receipt lines to catalogue products."""

from typing import Any

import httpx

from sali.cart_comparison.catalog import SupermarketsCatalog


def catalog_against(handler) -> tuple[SupermarketsCatalog, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    client = httpx.Client(transport=httpx.MockTransport(record))
    return SupermarketsCatalog("http://prices.test", client=client), seen


from sali.cart_comparison.matching import CartMatcher, is_barcode, similarity
from sali.receipt_extraction.models import Item


class FakeCatalog:
    """A catalogue whose contents each test states outright."""

    def __init__(
        self,
        by_barcode: dict[str, dict[str, Any]] | None = None,
        by_query: dict[str, list[dict[str, Any]]] | None = None,
    ) -> None:
        self._by_barcode = by_barcode or {}
        self._by_query = by_query or {}
        self.queries: list[str] = []

    def product_by_barcode(self, barcode: str) -> dict[str, Any] | None:
        return self._by_barcode.get(barcode)

    def search_products(self, query: str, *, limit: int = 25) -> list[dict[str, Any]]:
        self.queries.append(query)
        return self._by_query.get(query, [])


def product(barcode: int, name: str) -> dict[str, Any]:
    return {
        "id": str(barcode),
        "productBarcode": barcode,
        "productName": name,
        "manufacturerOrImporterName": "",
    }


def line(name: str, code: str | None = None) -> Item:
    return Item.model_validate(
        {
            "position": 1,
            "code": code,
            "name": name,
            "categories": [],
            "quantity": "1",
            "unit": "unit",
            "unit_price": "10.00",
            "gross_total": "10.00",
            "adjustments": [],
            "final_total": "10.00",
        }
    )


def test_only_catalogue_length_codes_count_as_barcodes() -> None:
    assert is_barcode("7290005271458")
    assert is_barcode("304819702099")
    # Weighed goods print a merchant-internal PLU, which the catalogue does not
    # key on, so it must never be looked up as a barcode.
    assert not is_barcode("595")
    assert not is_barcode("9951417")
    assert not is_barcode(None)
    assert not is_barcode("729000527145X")


def test_a_printed_barcode_matches_exactly_and_skips_the_name_search() -> None:
    catalog = FakeCatalog(by_barcode={"7290005271458": product(7290005271458, "ביצים")})
    match = CartMatcher(catalog).match(line("ביצים אורגני 12 יח", "7290005271458"))

    assert match.matched_by == "barcode"
    assert match.confidence == 1.0
    assert match.product is not None
    assert match.product.barcode == 7290005271458
    assert catalog.queries == []


def test_a_barcode_the_catalogue_lacks_is_reported_rather_than_guessed_by_name() -> (
    None
):
    catalog = FakeCatalog(by_query={"פתי בר קלאסי 500 גרם": [product(1, "פתי בר")]})
    match = CartMatcher(catalog).match(line("פתי בר קלאסי 500 גרם", "7290117765234"))

    assert match.product is None
    assert "not in the price database" in (match.reason or "")
    assert catalog.queries == []


def test_a_weighed_line_falls_back_to_the_name_search() -> None:
    catalog = FakeCatalog(by_query={"מלפפון": [product(2, "מלפפון")]})
    match = CartMatcher(catalog).match(line("מלפפון", "695"))

    assert match.matched_by == "name"
    assert match.product is not None
    assert match.product.name == "מלפפון"


def test_the_name_search_widens_to_single_words_only_when_the_full_name_fails() -> None:
    catalog = FakeCatalog(
        by_query={"שמפיניון": [product(3, "פטריות שמפיניון")]},
    )
    match = CartMatcher(catalog).match(line("פטריות שמפיניון טריות", "12"))

    assert catalog.queries[0] == "פטריות שמפיניון טריות"
    assert match.product is not None
    assert match.product.name == "פטריות שמפיניון"


def test_a_weak_name_match_is_refused_rather_than_priced_wrongly() -> None:
    # A discount trigger is not a product, and pricing the cart against whatever
    # it happens to resemble would corrupt every store total.
    catalog = FakeCatalog(by_query={"מפעיל הנחה 100 שח למ": [product(4, "מפעיל מיץ")]})
    match = CartMatcher(catalog).match(line("מפעיל הנחה 100 שח למ", "531"))

    assert match.product is None
    assert "confidence floor" in (match.reason or "")


def test_a_differing_pack_size_loses_to_the_matching_one() -> None:
    same_size = similarity("ממרח נוטלה 350 גרם", "נוטלה ממרח אגוזי לוז 350 גרם")
    wrong_size = similarity("ממרח נוטלה 350 גרם", "ממרח נוטלה 400 גרם")

    assert same_size > wrong_size


def test_a_truncated_receipt_word_still_matches_its_full_spelling() -> None:
    assert similarity("עגבניות שרי לובלו", "עגבניות שרי לובלו אר") > 0.8


def test_catalogue_rows_that_cannot_be_priced_are_never_matched() -> None:
    # The live catalogue returns rows like {"id": "7290000041179.0",
    # "productBarcode": 0}. They price against nothing, and because they all
    # share barcode 0 they would merge distinct products into one cart line.
    broken = {
        "id": "7290000041179.0",
        "productBarcode": 0,
        "productName": "מלפפון",
        "manufacturerOrImporterName": "",
    }
    catalog = FakeCatalog(by_query={"מלפפון": [broken]})

    match = CartMatcher(catalog).match(line("מלפפון", "695"))

    assert match.product is None


def test_a_usable_row_still_wins_when_a_broken_one_scores_the_same() -> None:
    broken = {
        "id": "7290000041179.0",
        "productBarcode": 0,
        "productName": "מלפפון",
        "manufacturerOrImporterName": "",
    }
    catalog = FakeCatalog(
        by_query={"מלפפון": [broken, product(7290000041179, "מלפפון")]}
    )

    match = CartMatcher(catalog).match(line("מלפפון", "695"))

    assert match.product is not None
    assert match.product.barcode == 7290000041179


def test_an_unrelated_product_scores_below_the_floor() -> None:
    assert similarity("מלפפון", "שוקולד מריר מעולה") == 0.0


def test_an_outage_is_not_reported_as_a_missing_product() -> None:
    """"Not in the database" is a claim about the shopper's shopping.

    Making it because somebody else's server was down tells them their milk
    is not sold anywhere, which is both false and unfalsifiable from the UI.
    """
    catalog, _ = catalog_against(lambda _request: httpx.Response(503))

    match = CartMatcher(catalog).match(line("חלב תנובה 3%", "7290000000001"))

    assert match.product is None
    assert match.reason is not None
    assert "could not be reached" in match.reason
    assert "is not in the price database" not in match.reason


def test_a_genuinely_absent_barcode_still_says_so() -> None:
    catalog, _ = catalog_against(lambda _request: httpx.Response(404))

    match = CartMatcher(catalog).match(line("חלב תנובה 3%", "7290000000001"))

    assert match.product is None
    assert match.reason == "barcode 7290000000001 is not in the price database"
