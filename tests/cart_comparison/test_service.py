"""Joining an extracted Receipt Document to the price database."""

from typing import Any

from sali.cart_comparison.service import CartComparisonService
from sali.receipt_extraction.models import (
    NormalizedReceipt,
    ReceiptDocument,
    validate_and_reconcile,
)


class FakeCatalog:
    """The price database, with exactly the contents a test needs."""

    def __init__(
        self,
        by_barcode: dict[str, dict[str, Any]] | None = None,
        by_query: dict[str, list[dict[str, Any]]] | None = None,
        comparisons: list[dict[str, Any]] | None = None,
    ) -> None:
        self._by_barcode = by_barcode or {}
        self._by_query = by_query or {}
        self._comparisons = comparisons or []
        self.compared: list[list[str]] = []

    def product_by_barcode(self, barcode: str) -> dict[str, Any] | None:
        return self._by_barcode.get(barcode)

    def search_products(self, query: str, *, limit: int = 25) -> list[dict[str, Any]]:
        return self._by_query.get(query, [])

    def compare_prices(
        self,
        product_ids: list[str],
        *,
        current_only: bool = True,
    ) -> list[dict[str, Any]]:
        self.compared.append(list(product_ids))
        wanted = set(product_ids)
        return [
            entry
            for entry in self._comparisons
            if str(entry["productBarcode"]) in wanted
        ]

    def stores(
        self,
        *,
        city: str | None = None,
        chain_id: str | None = None,
    ) -> list[dict[str, Any]]:
        return []


def catalogue_product(barcode: int, name: str) -> dict[str, Any]:
    return {
        "id": str(barcode),
        "productBarcode": barcode,
        "productName": name,
        "manufacturerOrImporterName": "",
    }


def priced(barcode: int, store_prices: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "productBarcode": barcode,
        "productName": f"product {barcode}",
        "currentOnly": True,
        "overallStatistics": {
            "minPrice": 0.0,
            "maxPrice": 0.0,
            "avgPrice": 0.0,
            "totalPriceRange": 0.0,
            "totalStores": 0,
            "totalChains": 0,
        },
        "chainComparison": [
            {
                "chainId": "c1",
                "chainName": "שופרסל",
                "storeCount": len(store_prices),
                "minPrice": 0.0,
                "maxPrice": 0.0,
                "avgPrice": 0.0,
                "priceRange": 0.0,
                "storePrices": store_prices,
            }
        ],
    }


MILK, BREAD = 7290000000001, 7290000000002


def document(lines: list[tuple[str, str | None, str, str]]) -> ReceiptDocument:
    """Build a reconciled Receipt Document from (name, code, qty, total) lines."""
    items = [
        {
            "position": position,
            "code": code,
            "name": name,
            "categories": [],
            "quantity": quantity,
            "unit": "unit",
            "unit_price": None,
            "gross_total": total,
            "adjustments": [],
            "final_total": total,
        }
        for position, (name, code, quantity, total) in enumerate(lines, start=1)
    ]
    paid = sum(float(total) for _, _, _, total in lines)
    return validate_and_reconcile(
        NormalizedReceipt.model_validate(
            {
                "merchant": {
                    "name": "סטופמרקט",
                    "branch_name": None,
                    "branch_number": None,
                },
                "transaction": {
                    "receipt_id": None,
                    "purchased_at": None,
                    "transaction_number": None,
                    "type": "purchase",
                    "currency": "ILS",
                },
                "totals": {
                    "subtotal": None,
                    "discounts": None,
                    "total": f"{paid:.2f}",
                },
                "items": items,
            }
        )
    )


def test_a_receipt_is_priced_across_stores_cheapest_complete_cart_first() -> None:
    catalog = FakeCatalog(
        by_barcode={
            str(MILK): catalogue_product(MILK, "חלב 3%"),
            str(BREAD): catalogue_product(BREAD, "לחם אחיד"),
        },
        comparisons=[
            priced(
                MILK,
                [{"storeId": "a", "price": 5.0}, {"storeId": "b", "price": 7.0}],
            ),
            priced(
                BREAD,
                [{"storeId": "a", "price": 12.0}, {"storeId": "b", "price": 8.0}],
            ),
        ],
    )
    receipt = document(
        [("חלב 3%", str(MILK), "1", "6.90"), ("לחם", str(BREAD), "1", "8.50")]
    )

    result = CartComparisonService(catalog).compare(receipt)

    assert len(result.matched) == 2
    assert result.unmatched == []
    assert [cart.store_id for cart in result.complete_carts] == ["b", "a"]
    assert [cart.total for cart in result.complete_carts] == ["15.00", "17.00"]
    assert result.receipt_total == "15.40"
    assert result.currency == "ILS"


def test_a_local_code_is_compared_through_equivalent_codes_at_other_stores() -> None:
    cucumber = "\u05de\u05dc\u05e4\u05e4\u05d5\u05df"
    decorated = (
        "\u05de\u05dc\u05e4\u05e4\u05d5\u05df/"
        "\u05d9\u05e8\u05e7\u05d5\u05ea "
        "\u05e9\u05e7\u05d9\u05dc"
    )
    catalog = FakeCatalog(
        by_barcode={"935": catalogue_product(935, decorated)},
        by_query={
            cucumber: [
                catalogue_product(935, decorated),
                catalogue_product(777104, cucumber),
            ]
        },
        comparisons=[
            priced(935, [{"storeId": "source", "price": 5.0}]),
            priced(777104, [{"storeId": "other", "price": 4.0}]),
        ],
    )

    result = CartComparisonService(catalog).compare(
        document([(cucumber, "935", "1", "5.50")])
    )

    assert result.matched[0].matched_by == "local_code"
    assert [item.product.barcode for item in result.matched[0].alternates] == [
        777104
    ]
    assert catalog.compared == [["935", "777104"]]
    assert {cart.store_id for cart in result.complete_carts} == {"source", "other"}


def test_unmatched_lines_are_reported_and_left_out_of_every_total() -> None:
    catalog = FakeCatalog(
        by_barcode={str(MILK): catalogue_product(MILK, "חלב 3%")},
        comparisons=[priced(MILK, [{"storeId": "a", "price": 5.0}])],
    )
    receipt = document(
        [
            ("חלב 3%", str(MILK), "1", "6.90"),
            ("מרשמלו אמריקאי", "7290019545620", "1", "12.00"),
        ]
    )

    result = CartComparisonService(catalog).compare(receipt)

    assert [line.receipt_name for line in result.unmatched] == ["מרשמלו אמריקאי"]
    assert result.complete_carts[0].total == "5.00"
    assert any("could not be matched" in warning for warning in result.warnings)


def test_an_empty_price_database_says_so_instead_of_returning_no_stores() -> None:
    catalog = FakeCatalog(
        by_barcode={str(MILK): catalogue_product(MILK, "חלב 3%")},
        comparisons=[],
    )

    result = CartComparisonService(catalog).compare(
        document([("חלב 3%", str(MILK), "1", "6.90")])
    )

    assert result.complete_carts == []
    assert result.partial_carts == []
    assert any("no current listings" in warning for warning in result.warnings)


def test_an_uncertain_name_match_is_priced_but_flagged() -> None:
    # `תפו"א לבן` against `תפוא אדום` is the same vegetable in the wrong colour:
    # close enough to price, close enough to be wrong, so the shopper is told.
    catalog = FakeCatalog(
        by_query={
            "תפו א לבן בתפזורת": [catalogue_product(99, "תפוא אדום בתפזורת")],
        },
        comparisons=[priced(99, [{"storeId": "a", "price": 4.0}])],
    )

    result = CartComparisonService(catalog).compare(
        document([('תפו"א לבן בתפזורת', "756", "1", "5.00")])
    )

    assert len(result.matched) == 1
    assert result.matched[0].matched_by == "name"
    assert any(warning.startswith("uncertain:") for warning in result.warnings)


def test_every_matched_product_is_priced_exactly_once() -> None:
    catalog = FakeCatalog(
        by_barcode={
            str(MILK): catalogue_product(MILK, "חלב 3%"),
            str(BREAD): catalogue_product(BREAD, "לחם אחיד"),
        },
    )

    CartComparisonService(catalog).compare(
        document(
            [
                ("חלב 3%", str(MILK), "1", "6.90"),
                # The same product bought twice must not be priced twice.
                ("חלב 3%", str(MILK), "1", "6.90"),
                ("לחם", str(BREAD), "1", "8.50"),
            ]
        )
    )

    assert catalog.compared == [[str(MILK), str(BREAD)]]
